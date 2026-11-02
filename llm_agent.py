import json
import anthropic

SYSTEM_PROMPT = """You are a disciplined, risk-averse XAUUSD (gold) trading analyst.
You review trade signals produced by a rule-based system and decide whether to APPROVE or REJECT.
Reject when: price is overextended, the move looks exhausted, volatility (ATR) is abnormal,
the setup contradicts the recent structure, or you are uncertain. Capital preservation comes first.
Respond with ONLY a JSON object:
{"decision": "APPROVE" | "REJECT", "confidence": <0.0-1.0>, "reason": "<short explanation>"}"""


class LLMReviewer:
    def __init__(self, model: str, min_confidence: float = 0.6):
        self.client = anthropic.Anthropic()  # Membaca ANTHROPIC_API_KEY dari environment
        self.model = model
        self.min_confidence = min_confidence

    def review(self, df, signal, order):
        cols = ["open", "high", "low", "close", "ema_fast", "ema_slow", "ema_trend", "rsi", "atr"]
        recent = df[cols].tail(30).round(2).to_csv()
        prompt = (
            f"Proposed trade: {order.side} {order.lots} lots XAUUSD\n"
            f"Entry: {order.entry}  SL: {order.sl}  TP: {order.tp}\n"
            f"Signal reason: {signal.reason}\n\n"
            f"Last 30 closed bars:\n{recent}"
        )
        try:
            msg = self.client.messages.create(
                model=self.model,
                max_tokens=400,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
            text = msg.content[0].text
            data = json.loads(text[text.find("{"): text.rfind("}") + 1])
            approved = (data.get("decision") == "APPROVE"
                        and float(data.get("confidence", 0)) >= self.min_confidence)
            return approved, data.get("reason", "")
        except Exception as e:
            # Fail-safe: jika LLM error, JANGAN trade
            return False, f"LLM error: {e}"
