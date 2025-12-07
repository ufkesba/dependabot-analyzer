'use client';

import Link from 'next/link';
import { Shield, Zap, Brain, GitBranch } from 'lucide-react';

export default function Home() {
  return (
    <div className="min-h-screen bg-[var(--background)]">
      {/* Header */}
      <header className="border-b border-[var(--border)]">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Shield className="w-8 h-8 text-primary-500" />
            <span className="text-xl font-bold">GitHub Alert Analyzer</span>
          </div>
          <div className="flex items-center gap-4">
            <Link href="/auth/login" className="text-[var(--muted)] hover:text-[var(--foreground)] transition-colors">
              Sign in
            </Link>
            <Link href="/auth/register" className="btn-primary">
              Get Started
            </Link>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <section className="py-24 px-6">
        <div className="max-w-4xl mx-auto text-center">
          <h1 className="text-5xl md:text-6xl font-bold mb-6 bg-gradient-to-r from-primary-400 to-primary-600 bg-clip-text text-transparent animate-fade-in">
            Security Alerts,
            <br />
            Intelligently Analyzed
          </h1>
          <p className="text-xl text-[var(--muted)] mb-10 max-w-2xl mx-auto animate-slide-up">
            Transform your Dependabot alerts into actionable insights with AI-powered analysis. 
            Prioritize what matters, understand the risks, and fix vulnerabilities faster.
          </p>
          <div className="flex gap-4 justify-center animate-slide-up" style={{ animationDelay: '0.2s' }}>
            <Link href="/auth/register" className="btn-primary text-lg px-8 py-3">
              Start Analyzing
            </Link>
            <Link href="#features" className="btn-secondary text-lg px-8 py-3">
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="py-24 px-6 border-t border-[var(--border)]">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center mb-16">Powerful Features</h2>
          <div className="grid md:grid-cols-3 gap-8">
            <FeatureCard
              icon={<Brain className="w-10 h-10 text-primary-500" />}
              title="AI-Powered Analysis"
              description="Leverage Claude and GPT models to understand vulnerability context, exploitability, and real-world impact."
            />
            <FeatureCard
              icon={<GitBranch className="w-10 h-10 text-primary-500" />}
              title="GitHub Integration"
              description="Seamlessly sync your repositories and Dependabot alerts with OAuth authentication."
            />
            <FeatureCard
              icon={<Zap className="w-10 h-10 text-primary-500" />}
              title="Smart Prioritization"
              description="Filter, sort, and prioritize alerts based on severity, confidence scores, and AI recommendations."
            />
          </div>
        </div>
      </section>

      {/* Stats Preview */}
      <section className="py-24 px-6 bg-[var(--card)]">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-4 gap-8 text-center">
            <StatCard value="100+" label="Vulnerabilities Analyzed" />
            <StatCard value="5+" label="LLM Providers Supported" />
            <StatCard value="<2min" label="Average Analysis Time" />
            <StatCard value="99.9%" label="Uptime" />
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="py-24 px-6">
        <div className="max-w-3xl mx-auto text-center">
          <h2 className="text-3xl font-bold mb-6">Ready to secure your code?</h2>
          <p className="text-[var(--muted)] mb-8">
            Join developers who use AI to understand and prioritize security vulnerabilities.
          </p>
          <Link href="/auth/register" className="btn-primary text-lg px-8 py-3">
            Get Started Free
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-[var(--border)] py-8 px-6">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-primary-500" />
            <span className="font-medium">GitHub Alert Analyzer</span>
          </div>
          <p className="text-sm text-[var(--muted)]">
            © 2024 GitHub Alert Analyzer. Built with Next.js and FastAPI.
          </p>
        </div>
      </footer>
    </div>
  );
}

function FeatureCard({ icon, title, description }: { icon: React.ReactNode; title: string; description: string }) {
  return (
    <div className="card card-hover">
      <div className="mb-4">{icon}</div>
      <h3 className="text-xl font-semibold mb-2">{title}</h3>
      <p className="text-[var(--muted)]">{description}</p>
    </div>
  );
}

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div>
      <div className="text-4xl font-bold text-primary-500 mb-2">{value}</div>
      <div className="text-[var(--muted)]">{label}</div>
    </div>
  );
}
