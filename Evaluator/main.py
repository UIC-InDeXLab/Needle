import csv
import json
import os
from datetime import datetime
from statistics import mean, variance
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, Query
from starlette.middleware.cors import CORSMiddleware
from tqdm import tqdm

from models import load_datasets
from search_engine import CLIPEngine, NeedleEngine
from utils import select_k_categories, check_category, get_category_counts

load_dotenv()

app = FastAPI()

origins = ["http://localhost:3000", "http://127.0.0.1:3000", os.getenv("PUBLIC_IP", "http://127.0.0.1:3000")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

datasets = load_datasets('./config.json')

CSV_FILE_PATH = "feedback.csv"

with open(CSV_FILE_PATH, mode="a", newline="") as file:
    writer = csv.writer(file)
    file.seek(0, 2)  # Move to the end of the file
    if file.tell() == 0:
        writer.writerow(["Query", "Preferred Engine"])


def calculate_average_precision(rankings, r) -> float:
    score = 0
    for i, pos in enumerate(rankings, start=1):
        score += i / pos
        if i == r:
            break
    return score / r


def calculate_hit_rate(rankings, r) -> float:
    if len(rankings) >= r:
        return 1.0
    else:
        return len(rankings) / r


def truncate(text, num_words=70):
    words = text.split()

    if len(words) > num_words:
        truncated_text = ' '.join(words[:num_words])
    else:
        truncated_text = text

    return truncated_text


@app.get("/evaluate/")
def evaluate_search_engine(dataset_name: str, number_of_tests: int, images_count_per_query: int,
                           min_true_positive: int, desired_true_positive: int,
                           number_of_images_to_generate: List[int] = Query(None),
                           max_true_positive: int = 10000,
                           generated_image_size: List[int] = Query(None),
                           generator_engines: List[str] = Query(None)):
    if dataset_name not in datasets:
        raise HTTPException(status_code=404, detail="Dataset not found")

    dataset = datasets[dataset_name]

    categories, counts = select_k_categories(dataset.metadata, k=number_of_tests, min_count=min_true_positive,
                                             max_count=max_true_positive)

    print(categories)

    evaluation_methods = {
        "clip": CLIPEngine(),
        "needle": NeedleEngine()
    }

    total_scores = {str(k): {} for k in number_of_images_to_generate}

    for category in tqdm(categories):
        if "other" in category or "abused" in category or "stupid" in category:
            continue
        for name, engine in evaluation_methods.items():
            for k in number_of_images_to_generate:
                for image_size in generated_image_size:
                    total_scores[str(k)][str(image_size)] = total_scores[str(k)].get(str(image_size),
                                                                                     {"average_precision": {},
                                                                                      "min_true_positive": {}})
                    feedback = {}

                    total_scores[str(k)][str(image_size)]["average_precision"].setdefault(name, [])
                    total_scores[str(k)][str(image_size)]["min_true_positive"].setdefault(name, [])

                    try:
                        results, qid = engine.search(truncate(str(category).replace("_", " ")
                                                              .replace("(", "")
                                                              .replace(")", ""), num_words=50)
                                                     , images_count_per_query,
                                                     k=k,
                                                     image_size=image_size,
                                                     generator_engines=generator_engines)
                    except Exception as e:
                        continue

                    rankings = []
                    for pos, filename in enumerate(results, start=1):
                        feedback[filename] = check_category(dataset.metadata, filename, category)
                        if feedback[filename]:
                            rankings.append(pos)  # relevance score of 1 if found

                    # Calculate average precision
                    r = desired_true_positive if counts.get(category,
                                                            desired_true_positive) >= desired_true_positive else counts.get(
                        category)
                    ap = calculate_average_precision(rankings, r=r)
                    total_scores[str(k)][str(image_size)]["average_precision"][name].append((category, ap))
                    # Calculate the set-based score
                    true_positive_score = calculate_hit_rate(rankings, r=r)
                    total_scores[str(k)][str(image_size)]["min_true_positive"][name].append(
                        (category, true_positive_score))
                    print(f"k={k}, image_size={image_size}, category={category}, AP={ap}")
                    if engine.is_feedback_required and os.getenv("SUBMIT_FEEDBACK", "False").lower() in ["true", "t",
                                                                                                         "1"]:
                        engine.submit_feedback(feedback, qid)

    # Calculate mean and variance for both metrics
    for k in number_of_images_to_generate:
        for image_size in generated_image_size:
            for name, scores in total_scores[str(k)][str(image_size)]["average_precision"].items():
                m = mean([score for category, score in scores])
                v = variance([score for category, score in scores])
                total_scores[str(k)][str(image_size)]["average_precision"][name].append(('mean', m))
                total_scores[str(k)][str(image_size)]["average_precision"][name].append(('var', v))

            for name, scores in total_scores[str(k)][str(image_size)]["min_true_positive"].items():
                m = mean([score for category, score in scores])
                v = variance([score for category, score in scores])
                total_scores[str(k)][str(image_size)]["min_true_positive"][name].append(('mean', m))
                total_scores[str(k)][str(image_size)]["min_true_positive"][name].append(('var', v))

    print(total_scores)

    with open(
            f'logs/{datetime.now().isoformat()}_{dataset_name}_{images_count_per_query}_{number_of_images_to_generate}_{generated_image_size}.log',
            'a+') as f:
        json.dump({"scores": total_scores,
                   "config": {"dataset_name": dataset_name,
                              "number_of_tests": number_of_tests,
                              "images_count_per_query": images_count_per_query,
                              "min_true_positive": min_true_positive,
                              "max_true_positive": max_true_positive,
                              "number_of_images_to_generate": number_of_images_to_generate,
                              "generated_image_size": generated_image_size,
                              "generator_engines": generator_engines}}, f)
    return total_scores


@app.post("/evaluate/feedback/")
def evaluate_with_feedback(dataset_name: str, qid: int, query: str, images_count_per_query: int,
                           desired_true_positive: int):
    dataset = datasets[dataset_name]
    engine = NeedleEngine()
    try:
        results = engine.get_qid_results(qid=qid, n=images_count_per_query)
    except Exception as e:
        pass

    rankings = []
    feedback = {}
    counts = get_category_counts(dataset.metadata)

    for pos, filename in enumerate(results, start=1):
        feedback[filename] = check_category(dataset.metadata, filename, query)
        if feedback[filename]:
            rankings.append(pos)

    r = desired_true_positive if counts.get(query, desired_true_positive) >= desired_true_positive else counts.get(
        query)
    ap = calculate_average_precision(rankings, r=r)
    hit_rate = calculate_hit_rate(rankings, r=r)
    print(f"query={query}, AP={ap}, HR={hit_rate}")

    with open(f"{dataset.name}.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([query, qid, ap, hit_rate])

    if engine.is_feedback_required and os.getenv("SUBMIT_FEEDBACK", "False").lower() in ["true", "t",
                                                                                         "1"]:
        engine.submit_feedback(feedback, qid)

    return {"ap": ap, "hr": hit_rate}


@app.post("/submit-feedback")
async def submit_feedback(request: Request):
    data = await request.json()
    query = data.get("query")
    feedback = data.get("feedback")

    # Append feedback to the CSV file
    with open(CSV_FILE_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([query, feedback])

    return {"status": "success", "message": "Feedback saved successfully"}
