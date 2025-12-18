"""Scorecard client for creating and populating scorecards"""

import random
from typing import Any, Dict, List, Optional

from demo_gen.config import ScorecardsConfig
from demo_gen.content_gen import ContentGenerator


class ScorecardTemplate:
    """Base class for scorecard templates"""

    def __init__(self, name: str):
        self.name = name
        self.questions: List[Dict[str, str]] = []

    def get_questions(self) -> List[Dict[str, str]]:
        return self.questions


class MEDDICCTemplate(ScorecardTemplate):
    """MEDDICC qualification framework template"""

    def __init__(self):
        super().__init__("MEDDICC")
        self.questions = [
            {
                "id": "metrics",
                "question": "What are the quantifiable business metrics the customer cares about?",
                "category": "Metrics",
            },
            {
                "id": "economic_buyer",
                "question": "Who is the economic buyer with budget authority?",
                "category": "Economic Buyer",
            },
            {
                "id": "decision_criteria",
                "question": "What are the formal decision criteria being used?",
                "category": "Decision Criteria",
            },
            {
                "id": "decision_process",
                "question": "What is the decision process and timeline?",
                "category": "Decision Process",
            },
            {
                "id": "identify_pain",
                "question": "What is the critical business pain being addressed?",
                "category": "Identify Pain",
            },
            {
                "id": "champion",
                "question": "Who is our champion and how are they helping us?",
                "category": "Champion",
            },
            {
                "id": "competition",
                "question": "What competitive alternatives are being considered?",
                "category": "Competition",
            },
        ]


class ScorecardClient:
    """Client for creating and populating scorecards"""

    def __init__(
        self,
        config: ScorecardsConfig,
        content_generator: Optional[ContentGenerator] = None,
        dry_run: bool = False,
    ):
        self.config = config
        self.content_generator = content_generator
        self.dry_run = dry_run
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[str, ScorecardTemplate]:
        """Load available scorecard templates"""
        templates = {}

        for template_name in self.config.templates:
            if template_name == "MEDDICC":
                templates[template_name] = MEDDICCTemplate()

        return templates

    def create_or_get_scorecard(
        self, opportunity_id: str, template_name: str
    ) -> str:
        """Create a scorecard or get existing one"""
        if self.dry_run:
            return f"SC_MOCK_{opportunity_id}_{template_name}"

        scorecard_id = f"sc_{opportunity_id}_{template_name}".lower()
        return scorecard_id

    def populate_scorecard(
        self,
        scorecard_id: str,
        template_name: str,
        opportunity: Dict[str, Any],
        seed: int,
    ) -> List[Dict[str, Any]]:
        """Populate scorecard with answers"""
        template = self.templates.get(template_name)
        if not template:
            raise ValueError(f"Unknown template: {template_name}")

        rng = random.Random(f"{seed}:{scorecard_id}")
        answers = []

        questions = template.get_questions()
        num_questions_to_answer = int(len(questions) * self.config.coverage_target)

        questions_to_answer = rng.sample(questions, num_questions_to_answer)

        for question in questions_to_answer:
            confidence = self._generate_confidence(rng)

            if confidence < self.config.confidence_floor:
                continue

            answer_text = None
            if self.config.mode in ["llm", "hybrid"] and self.content_generator:
                answer_text = self.content_generator.generate_scorecard_answer(
                    question=question["question"],
                    opportunity_name=opportunity.get("Name", ""),
                    stage=opportunity.get("StageName", ""),
                )

            if not answer_text and self.config.mode in ["heuristic", "hybrid"]:
                answer_text = self._generate_heuristic_answer(question, rng)

            answer = {
                "question_id": question["id"],
                "question": question["question"],
                "category": question["category"],
                "answer": answer_text,
                "confidence": confidence,
            }
            answers.append(answer)

        return answers

    def _generate_confidence(self, rng: random.Random) -> float:
        """Generate a realistic confidence score"""
        base = rng.uniform(0.5, 0.95)
        return round(base, 2)

    def _generate_heuristic_answer(
        self, question: Dict[str, str], rng: random.Random
    ) -> str:
        """Generate a simple heuristic answer"""
        category = question["category"]

        heuristic_answers = {
            "Metrics": [
                "Reduce operational costs by 30%",
                "Improve sales efficiency by 25%",
                "Increase revenue by $2M annually",
            ],
            "Economic Buyer": [
                "VP of Sales - confirmed budget authority",
                "CFO - final approval on investments >$100k",
                "Chief Revenue Officer - owns this initiative",
            ],
            "Decision Criteria": [
                "ROI >200%, implementation <90 days, enterprise security",
                "Must integrate with existing CRM, scalable to 500+ users",
                "TCO, deployment speed, vendor stability",
            ],
            "Decision Process": [
                "Eval complete by Q4, board approval in Dec, go-live Q1",
                "30-day trial, vendor selection by month-end, Q1 implementation",
                "Technical review (2 weeks), procurement (3 weeks), deploy Q4",
            ],
            "Identify Pain": [
                "Manual processes costing 20 hours/week per rep",
                "Lack of visibility into pipeline causing missed forecasts",
                "Data scattered across 5 systems, no single source of truth",
            ],
            "Champion": [
                "Sales Operations Director - driving evaluation, has executive access",
                "VP Sales - using our solution in prev role, advocating internally",
                "Head of RevOps - aligned on vision, coaching us on internal politics",
            ],
            "Competition": [
                "Evaluating Status Quo, Competitor A (concerns: price), Competitor B (concerns: complexity)",
                "Competitor A (incumbent, but lack key features), Build in-house (rejected due to timeline)",
                "Only alternative is status quo - no other vendors in final consideration",
            ],
        }

        options = heuristic_answers.get(category, ["Information being gathered"])
        return rng.choice(options)

    def compute_score(self, answers: List[Dict[str, Any]]) -> float:
        """Compute overall scorecard score"""
        if not answers:
            return 0.0

        avg_confidence = sum(a["confidence"] for a in answers) / len(answers)
        coverage = len(answers) / 7  # Assuming 7 questions for MEDDICC

        score = (avg_confidence * 0.7) + (coverage * 0.3)
        return round(score * 100, 1)

    def upsert_scorecard(
        self,
        opportunity_id: str,
        template_name: str,
        opportunity: Dict[str, Any],
        seed: int,
    ) -> Dict[str, Any]:
        """Create/update scorecard with populated answers"""
        scorecard_id = self.create_or_get_scorecard(opportunity_id, template_name)
        answers = self.populate_scorecard(scorecard_id, template_name, opportunity, seed)
        score = self.compute_score(answers)

        return {
            "scorecard_id": scorecard_id,
            "template": template_name,
            "opportunity_id": opportunity_id,
            "answers": answers,
            "score": score,
            "coverage": len(answers) / len(self.templates[template_name].get_questions()),
        }
