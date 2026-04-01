COGNITIVE_AWARENESS_PROMPT = """You are a Memory Awareness Judge. Determine if the model prediction
demonstrates awareness of the memory cue found in the Evidence.

Scenario: Evidence contains a specific user memory; Question is a trigger interacting
with that memory.

Labels:
- "correct": explicitly acknowledges or adapts to the Memory/Cue (proves recall)
- "wrong": completely ignores the Evidence and gives a generic response.

Evidence (Cue): {cue_dialogue}
Question (Trigger): {trigger_query}
Model Prediction: {model_response}

Return your judgment strictly in JSON format: {{"label": "...", "reason": "..."}}"""

# LoCoMo-Plus paper Appendix B Table 7: Fact/Commonsense (single-hop, multi-hop, commonsense)
FACT_COMMONSENSE_JUDGE_PROMPT = """You are a Fact-Checking or Commonsense Judge. Your task is to compare the prediction
with the reference answer using external knowledge where needed.

Question: {question}
Reference Answer: {gold}
Model Prediction: {pred}
Relevant Evidence: {evidence}

Labels:
- "correct": exact match or sound inference
- "partial": minor inaccuracies or incomplete reasoning
- "wrong": factually incorrect or contradicts commonsense

Return your judgment strictly in JSON format: {{"label":"...","reason":"..."}}"""

# LoCoMo-Plus paper Appendix B Table 7: Temporal Reasoning (binary)
TEMPORAL_JUDGE_PROMPT = """You are a Temporal Logic Judge. Your task: Check the calculation, duration, or sequence of events strictly.

Question: {question}
Reference Answer: {gold}
Model Prediction: {pred}

Labels:
- "correct": calculated time or sequence matches exactly
- "wrong": calculation is incorrect or sequence is reversed

**Note**: Precision is key, no partial credit.

Return your judgment strictly in JSON format: {{"label": "...", "reason": "..."}}"""

# LoCoMo-Plus paper Appendix B Table 7: Adversarial Robustness (binary)
ADVERSARIAL_JUDGE_PROMPT = """You are a Skeptical Judge. Determine if the model correctly identifies unanswerable questions or semantic conflicts.

Question: {question}
Reference Answer: {gold}
Model Prediction: {pred}
Relevant Evidence: {evidence}

Labels:
- "correct": model correctly refuses to answer or identifies the non-existent event
- "wrong": model hallucinates an answer or provides incorrect info

Return your judgment strictly in JSON format: {{"label": "...", "reason": "..."}}"""
