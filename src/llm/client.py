import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import google.generativeai as genai
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Structured response from LLM"""
    content: str
    model: str
    tokens_used: Optional[int] = None


class LLMClient:
    """
    Wrapper for LLM API calls with support for multiple providers.
    Currently configured for Google AI Studio / Gemini.
    """

    def __init__(self, provider: str = "google", model: str = "gemini-flash-latest", api_key: Optional[str] = None, enable_logging: bool = True, agent_name: Optional[str] = None):
        self.provider = provider
        self.model = model
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        self.enable_logging = enable_logging
        self.agent_name = agent_name or "unknown"

        # Setup conversation logging
        if self.enable_logging:
            self.log_dir = Path("logs/conversations")
            self.log_dir.mkdir(parents=True, exist_ok=True)
            self.session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.conversation_count = 0

        if not self.api_key:
            raise ValueError(f"API key not found for provider: {provider}")

        # Configure Google AI
        if provider == "google":
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel(model)
        else:
            raise ValueError(f"Provider {provider} not yet implemented. Currently only 'google' is supported.")

    def _log_conversation(self, prompt: str, response_text: str, system_prompt: Optional[str] = None, metadata: Optional[Dict] = None):
        """Log conversation to file for debugging and improvement."""
        if not self.enable_logging:
            return

        self.conversation_count += 1
        log_file = self.log_dir / f"{self.agent_name}_{self.session_id}_{self.conversation_count:03d}.json"

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "session_id": self.session_id,
            "agent_name": self.agent_name,
            "conversation_number": self.conversation_count,
            "model": self.model,
            "system_prompt": system_prompt,
            "user_prompt": prompt,
            "response": response_text,
            "metadata": metadata or {}
        }

        with open(log_file, 'w') as f:
            json.dump(log_entry, f, indent=2)

    async def ask(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.1
    ) -> LLMResponse:
        """
        Send a prompt to the LLM and get a response.

        Args:
            prompt: The user prompt/question
            system_prompt: Optional system instructions
            max_tokens: Max tokens in response
            temperature: Creativity level (0.0-1.0)

        Returns:
            LLMResponse with content and metadata
        """
        try:
            # Combine system prompt if provided
            full_prompt = prompt
            if system_prompt:
                full_prompt = f"{system_prompt}\n\n{prompt}"

            # Generate response
            response = self.client.generate_content(
                full_prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_tokens,
                    temperature=temperature,
                )
            )

            tokens_used = response.usage_metadata.total_token_count if hasattr(response, 'usage_metadata') else None

            # Log the conversation
            self._log_conversation(
                prompt=prompt,
                response_text=response.text,
                system_prompt=system_prompt,
                metadata={
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "tokens_used": tokens_used
                }
            )

            return LLMResponse(
                content=response.text,
                model=self.model,
                tokens_used=tokens_used
            )

        except Exception as e:
            raise RuntimeError(f"LLM API call failed: {str(e)}")

    async def ask_structured(
        self,
        prompt: str,
        response_format: Dict,
        system_prompt: Optional[str] = None,
        max_tokens: int = 8192,
        temperature: float = 0.1
    ) -> Dict:
        """
        Request a structured JSON response from the LLM.

        Args:
            prompt: The user prompt
            response_format: Dict describing the expected JSON structure
            system_prompt: Optional system instructions
            max_tokens: Max tokens in response
            temperature: Creativity level

        Returns:
            Parsed JSON response as dict
        """
        # Add JSON formatting instructions to prompt
        format_instructions = f"""

Respond ONLY with valid JSON matching this structure:
{json.dumps(response_format, indent=2)}

CRITICAL JSON FORMATTING RULES:
- Use proper JSON escaping for all strings
- Escape newlines as \\n (NOT actual line breaks)
- Escape quotes as \\"
- Escape backslashes as \\\\
- Keep string values reasonably concise (max 1500 chars per field)
- For test_case: keep it brief (max 300 chars) or set to null
- Do NOT include actual newlines or line breaks inside string values
- Ensure ALL strings are properly terminated with closing quotes
- Test your JSON is valid before responding"""
        enhanced_prompt = prompt + format_instructions

        response = await self.ask(enhanced_prompt, system_prompt, max_tokens, temperature)

        # Try to parse JSON from response
        try:
            # Extract JSON from markdown code blocks if present
            content = response.content.strip()

            # Remove markdown code block markers
            if content.startswith("```json"):
                content = content[7:]  # Remove ```json
            elif content.startswith("```"):
                content = content[3:]  # Remove ```

            # Find the closing ```
            if "```" in content:
                content = content.split("```")[0]

            content = content.strip()

            # Try to parse
            return json.loads(content)

        except json.JSONDecodeError as e:
            # Try to find JSON object boundaries and extract
            try:
                start = response.content.find('{')
                end = response.content.rfind('}')
                if start != -1 and end != -1:
                    content = response.content[start:end+1]
                    return json.loads(content)
            except:
                pass
            
            # Try to repair common JSON issues
            try:
                content = response.content
                # Remove markdown blocks
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                # Find JSON boundaries
                start = content.find('{')
                end = content.rfind('}')
                if start != -1 and end != -1:
                    json_str = content[start:end+1]
                    
                    # Try to fix unterminated strings by finding incomplete field
                    # Split by lines and check for proper closing
                    lines = json_str.split('\n')
                    fixed_lines = []
                    in_string = False
                    
                    for i, line in enumerate(lines):
                        # Count unescaped quotes to detect unterminated strings
                        quote_count = 0
                        j = 0
                        while j < len(line):
                            if line[j] == '"' and (j == 0 or line[j-1] != '\\'):
                                quote_count += 1
                            j += 1
                        
                        # If odd number of quotes, string is unterminated
                        if quote_count % 2 == 1:
                            # Terminate the string and try to close the object properly
                            if i == len(lines) - 1 or not line.rstrip().endswith(','):
                                line = line.rstrip() + '"'
                        
                        fixed_lines.append(line)
                    
                    # Try parsing the fixed JSON
                    fixed_json = '\n'.join(fixed_lines)
                    
                    # If still incomplete, try to close the JSON object
                    open_braces = fixed_json.count('{') - fixed_json.count('}')
                    if open_braces > 0:
                        fixed_json += '\n}' * open_braces
                    
                    return json.loads(fixed_json)
            except Exception as repair_error:
                # If repair failed, provide detailed error
                pass

            raise ValueError(f"LLM did not return valid JSON: {str(e)}\n\nResponse excerpt: {response.content[:1000]}...\n\nTry reducing max_tokens or simplifying the prompt.")
