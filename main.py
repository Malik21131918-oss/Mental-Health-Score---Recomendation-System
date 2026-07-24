from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "model.pkl"


def load_model():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"model.pkl not found.\nExpected Location: {MODEL_PATH}"
        )

    return joblib.load(MODEL_PATH)


model = load_model()


app = FastAPI(
    title="AI Mental Health Insight & Recommendation System",
    description="""
Predict a user's Mental Health Score based on lifestyle,
social media usage and daily habits.

The API also provides:

• Risk Classification

• Lifestyle Analysis

• Personalized Recommendations
""",
    version="2.0.0",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TOP_COUNTRIES = {
    "India",
    "USA",
    "Canada",
    "Australia",
    "UK",
    "Germany",
    "Mexico",
    "Turkey",
    "France",
}


class MentalHealthInput(BaseModel):

    age: int = Field(..., ge=10, le=100)

    gender: Literal[
        "Male",
        "Female",
    ]

    country: str

    academic_level: Literal[
        "High School",
        "Undergraduate",
        "Graduate",
    ]

    most_used_platform: Literal[
        "Facebook",
        "Instagram",
        "YouTube",
        "Twitter",
        "TikTok",
        "LinkedIn",
        "Snapchat",
        "WhatsApp",
        "WeChat",
        "LINE",
        "KakaoTalk",
        "VKontakte",
    ]

    purpose_of_use: Literal[
        "Education",
        "Entertainment",
        "Networking",
        "News",
    ]

    avg_daily_usage_hours: float = Field(
        ...,
        ge=0,
        le=24,
    )

    daily_unlocks: int = Field(
        ...,
        ge=0,
    )

    study_hours: float = Field(
        ...,
        ge=0,
        le=24,
    )

    physical_activity_hours: float = Field(
        ...,
        ge=0,
        le=24,
    )

    sleep_hours_per_night: float = Field(
        ...,
        ge=0,
        le=24,
    )

    stress_level: Literal[
        "Low",
        "Medium",
        "High",
        "Very High",
    ]


class PredictionResponse(BaseModel):

    predicted_score: float


class AnalysisResponse(BaseModel):

    mental_health_score: float

    risk_level: str

    top_factors: list[str]

    recommendations: list[str]

    summary: str


def build_dataframe(data: MentalHealthInput) -> pd.DataFrame:

    grouped_country = (
        data.country
        if data.country in TOP_COUNTRIES
        else "Other"
    )

    return pd.DataFrame(
        [
            {
                "Age": data.age,
                "Gender": data.gender,
                "Country": data.country,
                "Academic_Level": data.academic_level,
                "Most_Used_Platform": data.most_used_platform,
                "Purpose_Of_Use": data.purpose_of_use,
                "Avg_Daily_Usage_Hours": data.avg_daily_usage_hours,
                "Daily_Unlocks": data.daily_unlocks,
                "Study_Hours": data.study_hours,
                "Physical_Activity_Hours": data.physical_activity_hours,
                "Sleep_Hours_Per_Night": data.sleep_hours_per_night,
                "Stress_Level": data.stress_level,
                "Grouped_Country": grouped_country,
            }
        ]
    )

def get_risk_level(score: float) -> str:

    if score >= 8:
        return "Healthy"

    if score >= 6:
        return "Mild Concern"

    if score >= 4:
        return "Moderate Risk"

    return "High Risk"


def get_top_factors(top_n: int = 5) -> list[str]:

    try:

        preprocessor = model.named_steps["preprocessor"]

        estimator = None

        for name in ["model", "regressor", "random_forest"]:
            if name in model.named_steps:
                estimator = model.named_steps[name]
                break

        if estimator is None:
            return []

        feature_names = preprocessor.get_feature_names_out()

        importance = estimator.feature_importances_

        ranked_features = sorted(
            zip(feature_names, importance),
            key=lambda item: item[1],
            reverse=True,
        )

        cleaned_features = []

        for feature, _ in ranked_features[:top_n]:

            feature = feature.split("__")[-1]

            feature = feature.replace("_", " ")

            cleaned_features.append(feature)

        return cleaned_features

    except Exception:

        return []


def generate_recommendations(
    data: MentalHealthInput,
) -> list[str]:

    recommendations = []

    if data.sleep_hours_per_night < 6:
        recommendations.append(
            "Increase your sleep to 7–8 hours every night."
        )

    if data.avg_daily_usage_hours > 5:
        recommendations.append(
            "Reduce daily social media usage to less than 3 hours."
        )

    if data.daily_unlocks > 100:
        recommendations.append(
            "Reduce unnecessary phone checking throughout the day."
        )

    if data.physical_activity_hours < 1:
        recommendations.append(
            "Exercise for at least 30 minutes every day."
        )

    if data.study_hours < 2:
        recommendations.append(
            "Increase productive study time and reduce distractions."
        )

    if data.stress_level in ["High", "Very High"]:
        recommendations.append(
            "Practice stress management through meditation, breathing exercises, or outdoor activities."
        )

    if (
        data.sleep_hours_per_night >= 7
        and data.avg_daily_usage_hours <= 3
        and data.physical_activity_hours >= 1
        and data.stress_level == "Low"
    ):
        recommendations.append(
            "Your lifestyle looks balanced. Keep maintaining these healthy habits."
        )

    return recommendations


def generate_summary(
    score: float,
    risk_level: str,
    recommendations: list[str],
) -> str:

    if risk_level == "Healthy":

        return (
            f"Your predicted Mental Health Score is {score:.2f}. "
            "Your daily routine appears healthy and well balanced. "
            "Continue maintaining your positive lifestyle habits."
        )

    if risk_level == "Mild Concern":

        return (
            f"Your predicted Mental Health Score is {score:.2f}. "
            "There are a few lifestyle habits that could be improved. "
            "Small changes may significantly improve your overall well-being."
        )

    if risk_level == "Moderate Risk":

        return (
            f"Your predicted Mental Health Score is {score:.2f}. "
            "Your current habits indicate moderate mental health risk. "
            "Following the recommendations may improve your mental well-being."
        )

    return (
        f"Your predicted Mental Health Score is {score:.2f}. "
        "Your lifestyle indicates a high mental health risk. "
        "Improving sleep, reducing social media usage, increasing physical activity, "
        "and managing stress should be your highest priorities."
    )


def predict_score(data: MentalHealthInput) -> float:

    try:

        dataframe = build_dataframe(data)

        prediction = model.predict(dataframe)[0]

        return round(float(prediction), 2)

    except Exception as error:

        raise HTTPException(
            status_code=400,
            detail=f"Prediction failed: {error}",
        )

@app.get(
    "/",
    tags=["Home"],
)
def home():

    return {
        "project": "AI Mental Health Insight & Recommendation System",
        "model": "Random Forest Regressor",
        "version": "2.0.0",
        "status": "Running",
        "docs": "/docs",
    }


@app.get(
    "/health",
    tags=["Health"],
)
def health():

    return {
        "status": "Healthy",
        "model_loaded": model is not None,
    }


@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Prediction"],
)
def predict(data: MentalHealthInput):

    score = predict_score(data)

    return PredictionResponse(
        predicted_score=score,
    )


@app.post(
    "/analyze",
    response_model=AnalysisResponse,
    tags=["Analysis"],
)
def analyze(data: MentalHealthInput):

    score = predict_score(data)

    risk_level = get_risk_level(score)

    top_factors = get_top_factors()

    recommendations = generate_recommendations(data)

    summary = generate_summary(
        score,
        risk_level,
        recommendations,
    )

    return AnalysisResponse(
        mental_health_score=score,
        risk_level=risk_level,
        top_factors=top_factors,
        recommendations=recommendations,
        summary=summary,
    )


if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )