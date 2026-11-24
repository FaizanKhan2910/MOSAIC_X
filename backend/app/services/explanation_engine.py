from typing import Dict, Any, List
from backend.app.models.schema import DiscoveryItem

class ExplanationEngine:
    @staticmethod
    def generate_plain_explanation(discovery: DiscoveryItem) -> str:
        """
        Synthesizes statistical evidence into an explainable, non-hallucinatory narrative.
        Never fabricates metrics, health claims, or causal mechanisms.
        """
        sig_a = discovery.signal_a.replace("_", " ")
        sig_b = discovery.signal_b.replace("_", " ")
        r = discovery.correlation_coefficient
        p = discovery.p_value
        n = discovery.valid_observations

        trend = "positive" if r > 0 else "inverse"
        strength = discovery.statistical_strength.lower()

        lines = [
            f"**Observed Association:** Across {n} paired days ({discovery.observation_window}), "
            f"we measured a {strength} {trend} statistical correlation (r = {r:.2f}, p = {p:.4f}).",
            f"**Evidence & Effect:** {discovery.effect_size}.",
            "**Causal Warning:** NEXORA strictly separates correlation from causation. "
            "Observational pairing does not prove that changing one variable will automatically alter the other.",
            f"**Plausible Alternative Confounder:** {discovery.possible_alternative_explanations[0] if discovery.possible_alternative_explanations else 'Environmental variance.'}"
        ]

        return "\n\n".join(lines)
