"""LLM-powered content generation for realistic activity descriptions"""

import os
from typing import Optional

import openai

from demo_gen.config import LLMConfig


class ContentGenerator:
    """Generates realistic content for meetings and emails using LLM"""

    def __init__(self, config: LLMConfig):
        self.config = config
        self.enabled = config.enabled

        if self.enabled:
            self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize OpenAI client"""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        if self.config.provider == "openai":
            self.client = openai.OpenAI(api_key=api_key)
        elif self.config.provider == "azure_openai":
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            if not azure_endpoint:
                raise ValueError("AZURE_OPENAI_ENDPOINT environment variable not set")
            self.client = openai.AzureOpenAI(
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version="2024-02-01",
            )

    def generate_meeting_notes(
        self,
        subject: str,
        opportunity_name: str,
        stage: str,
        participants: list,
        when: str = "past",
    ) -> Optional[str]:
        """Generate realistic meeting notes"""
        if not self.enabled:
            return None

        prompt = f"""Generate brief, realistic meeting notes for a B2B sales meeting.

Meeting: {subject}
Opportunity: {opportunity_name}
Stage: {stage}
Participants: {', '.join(participants)}
Timing: {"Completed" if when == "past" else "Upcoming"}

{"Write 2-3 bullet points summarizing what was discussed and next steps." if when == "past" else "Write 1-2 sentences about the meeting agenda."}

Keep it professional and concise."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sales professional writing concise meeting notes.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Warning: LLM generation failed: {e}")
            return None

    def generate_email_body(
        self,
        subject: str,
        opportunity_name: str,
        stage: str,
        when: str = "past",
    ) -> Optional[str]:
        """Generate realistic email body"""
        if not self.enabled:
            return None

        prompt = f"""Generate a brief, realistic email body for a B2B sales email.

Subject: {subject}
Opportunity: {opportunity_name}
Stage: {stage}
Timing: {"Sent" if when == "past" else "Draft"}

Write 2-3 short paragraphs. Keep it professional and to the point."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sales professional writing concise emails.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Warning: LLM generation failed: {e}")
            return None

    def generate_scorecard_answer(
        self,
        question: str,
        opportunity_name: str,
        stage: str,
        context: Optional[str] = None,
    ) -> Optional[str]:
        """Generate a realistic scorecard answer"""
        if not self.enabled:
            return None

        context_str = f"\nContext: {context}" if context else ""

        prompt = f"""Generate a brief, realistic answer for this sales qualification question.

Question: {question}
Opportunity: {opportunity_name}
Stage: {stage}{context_str}

Provide a concise answer (1-2 sentences) that sounds like it came from actual discovery conversations."""

        try:
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a sales professional documenting qualification criteria.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
            )

            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Warning: LLM generation failed: {e}")
            return None
