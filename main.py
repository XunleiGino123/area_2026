import argparse
import asyncio
import os
import re
from collections import Counter

import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv
from autogen_agentchat.agents import AssistantAgent
from autogen_ext.models.openai import OpenAIChatCompletionClient

# -------------------------------
# Load .env and configure Gemini API
# -------------------------------
load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def parse_args():
    parser = argparse.ArgumentParser(description="Run Unit4.1 Q6 grading with 5 Gemini agents.")
    parser.add_argument(
        "-n", "--samples",
        type=int,
        default=None,
        help="Number of samples to grade (default: all rows in CSV). E.g. -n 10 or --samples 213",
    )
    parser.add_argument(
        "--input",
        type=str,
        default="U4.1Q6final.csv",
        help="Input CSV path (default: U4.1Q6final.csv)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="geology_q6_87.csv",
        help="Output CSV path (default: geology_q6_87.csv)",
    )
    return parser.parse_args()


# -------------------------------
# Load your CSV file (sample limit applied in main)
# -------------------------------
args = parse_args()
input_file = args.input
df = pd.read_csv(input_file, encoding='ISO-8859-1')
if args.samples is not None:
    df = df.iloc[: args.samples]
print(f"Grading {len(df)} samples from {input_file}")

# -------------------------------
# Import your base prompts
# -------------------------------
from prompts import (
    base_prompt1, base_prompt2, base_prompt3, base_prompt4, base_prompt5
)
# -------------------------------
# Prepare base prompts and number of graders
# -------------------------------
grading_prompts = [base_prompt1, base_prompt2, base_prompt3, base_prompt4, base_prompt5]
N_GRADERS = 5

# -------------------------------
# Define the Gemini client class
# -------------------------------
class GeminiClient:
    def __init__(self, model_name="gemini-2.5-flash"):
        self.model_name = model_name

    async def generate(self, prompt):
        model = genai.GenerativeModel(self.model_name)
        response = model.generate_content(prompt)
        return response.text.strip() if response and response.text else ""

# -------------------------------
# Grade extractor (0–3). 
# -------------------------------
GRADE_REGEX = re.compile(r'\b[0-4]\b')

def extract_grade(reply: str):
    m = GRADE_REGEX.search(reply or "")
    return int(m.group()) if m else None

# -------------------------------
# Multi-agent task function (graders + evaluator)
# -------------------------------
async def multi_agent_task(ans, idx, expert_grade1, expert_grade2):
    gemini_client = GeminiClient()
    agent_tasks = []

    for i in range(N_GRADERS):
        base_prompt = grading_prompts[i]
        prompt = f"{base_prompt}\n\nStudent answer:\n{ans}"

        async def agent_task(agent_num=i+1, prompt_text=prompt):
            response = await gemini_client.generate(prompt_text)
            reply = (response or "").strip()
            match = GRADE_REGEX.search(reply)
            grade = int(match.group()) if match else None
            print(f"Agent {agent_num} Response:\n{reply}")
            return grade, reply

        agent_tasks.append(agent_task())

    # Run graders (agents 1–5)
    grading_results = await asyncio.gather(*agent_tasks)

    # Extract grades and explanations
    agent_grades = [g for g, _ in grading_results]
    agent_explanations = [e for _, e in grading_results]

    # -------------------------------
    # Agent 6: Evaluator of other agents
    # -------------------------------
    combined_feedback = "\n".join(
        [f"Agent {i+1} Grade: {agent_grades[i]}\nAgent {i+1} Explanation:\n{agent_explanations[i]}"
         for i in range(N_GRADERS)]
    )
    #evaluation_prompt = f"""{base_prompt2}

#Now, evaluate the consistency and accuracy of the following grading responses given a student answer.

#Student Answer:
#{ans}

#Grading Responses from Agents 1 to 5:
#{combined_feedback}

#Please provide an analysis about whether these grades are reasonable, consistent, and how confident you are in the ensemble judgment."""
#    evaluator_response = await gemini_client.generate(evaluation_prompt)
#    print("Agent 6 (Evaluator) Response:\n", evaluator_response)

    # -------------------------------
    # Agreement checks (NEW/CHANGED)
    # -------------------------------

    counts = Counter(g for g in agent_grades if g is not None)
    if counts:
        top_grade, top_count = counts.most_common(1)[0]
    else:
        top_grade, top_count = (None, 0)


    agent_agree = int(top_count >= 4)                      
    agent_unanimous = int(top_count == 5)                
    agent_consensus_grade = top_grade if top_count >= 4 else None  


    agent_unanimous_grade = agent_consensus_grade          


    record = {
        "student_answer": ans,
        "Expert1 grade": expert_grade1,
        "Expert2 grade": expert_grade2,
        "expert_agree": int(expert_grade1 == expert_grade2),
        "agent_agree": agent_agree,
        "agent_unanimous": agent_unanimous,              
        "agent_consensus_grade": agent_consensus_grade,   
        "agent_unanimous_grade": agent_unanimous_grade,   
        "agent_majority_vote": top_grade if counts else None,  
        "agent_grades": str(agent_grades),
        #"agent6_evaluator_comment": evaluator_response
    }

    for agent, (grade, explanation) in enumerate(grading_results, start=1):
        record[f"ai_grade_agent_{agent}"] = grade
        record[f"ai_explanation_agent_{agent}"] = explanation

    print(f"[{idx + 1}/{len(df)}] Done. expert_agree={int(expert_grade1 == expert_grade2)}, agent_agree={agent_agree}")
    return record

# -------------------------------
# Main grading loop
# -------------------------------
async def grade_all_records():
    all_records = []

    for idx, row in df.iterrows():
        ans = row.iloc[0]
        expert_grade1 = row.iloc[1]
        expert_grade2 = row.iloc[3]
        print(f"\nGrading answer #{idx + 1}")
        print("Student Answer:", ans)

        record = await multi_agent_task(ans, idx, expert_grade1, expert_grade2)
        all_records.append(record)

    # Save to CSV
    graded_df = pd.DataFrame(all_records)
    out_csv = args.output
    graded_df.to_csv(out_csv, index=False)
    print(f"Done: Results saved to {out_csv}")

    # ---------------------------
    # Final rates (NEW/CHANGED to use consensus)
    # ---------------------------
    if len(graded_df) == 0:
        print("No records graded. Rates cannot be computed.")
        return


    expert_agree_rate = graded_df["expert_agree"].mean()
    agent_agree_rate = graded_df["agent_agree"].mean()


    both_and_same_overall = (
        (graded_df["expert_agree"] == 1)
        & (graded_df["agent_agree"] == 1)
        & (graded_df["agent_consensus_grade"].notna())
        & (graded_df["Expert1 grade"] == graded_df["Expert2 grade"])
        & (graded_df["Expert1 grade"] == graded_df["agent_consensus_grade"])
    ).mean()

    both_mask = (
        (graded_df["expert_agree"] == 1)
        & (graded_df["agent_agree"] == 1)
        & (graded_df["agent_consensus_grade"].notna())
    )
    if both_mask.sum() > 0:
        both_and_same_conditional = (
            graded_df.loc[both_mask, :]
            .apply(lambda r: int(r["Expert1 grade"] == r["Expert2 grade"] == r["agent_consensus_grade"]), axis=1)
            .mean()
        )
    else:
        both_and_same_conditional = float('nan')

    print("\n========== SUMMARY ==========")
    print(f"Experts-and-agents SAME-GRADE RATE (overall): {both_and_same_overall:.4f}")
    print(f"Expert agree rate:                          {expert_agree_rate:.4f}")
    print(f"Agent agree rate:                           {agent_agree_rate:.4f}")
    print(f"Both-agree SAME-GRADE rate (conditional):   {both_and_same_conditional:.4f}")
    print("================================")

# Run the grading and evaluation
asyncio.run(grade_all_records())
