import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal

model = joblib.load('model.pkl')
top_countries = ['Other', 'India', 'USA', 'Canada', 'Australia', 'UK', 'Germany', 'Mexico', 'Turkey', 'France']

app = FastAPI(title="AI Mental Health Insight & Recommendation System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# Input schema
class StudentData(BaseModel):
    age                     : int   = Field(..., ge=10, le=100)
    gender                  : Literal['Male', 'Female']
    country                 : str
    academic_level          : Literal['Undergraduate', 'Graduate', 'High School']
    most_used_platform      : Literal['Facebook', 'LinkedIn', 'Instagram', 'Snapchat', 'Twitter', 'YouTube', 'TikTok', 'LINE', 'KakaoTalk', 'VKontakte', 'WhatsApp', 'WeChat']
    purpose_of_use          : Literal['Networking', 'Education', 'Entertainment', 'News']
    avg_daily_usage_hours   : float = Field(..., ge=0, le=24)
    daily_unlocks           : int   = Field(..., ge=0)
    study_hours             : float = Field(..., ge=0, le=24)
    physical_activity_hours : float = Field(..., ge=0, le=24)
    sleep_hours_per_night   : float = Field(..., ge=0, le=24)
    stress_level            : Literal['Low', 'Medium', 'High', 'Very High']


# Response schemas
class PredictionResponse(BaseModel):
    predicted_mental_health_score: float


class AnalysisResponse(BaseModel):
    mental_health_score: float
    risk_level: str
    top_factors: list[str]
    recommendations: list[str]
    summary: str


def build_input_row(data: StudentData) -> pd.DataFrame:
    country_group = data.country if data.country in top_countries else "Other"

    return pd.DataFrame([{
        'Age'                      : data.age,
        'Gender'                   : data.gender,
        'Country'                  : data.country,
        'Academic_Level'           : data.academic_level,
        'Most_Used_Platform'       : data.most_used_platform,
        'Purpose_Of_Use'           : data.purpose_of_use,
        'Avg_Daily_Usage_Hours'    : data.avg_daily_usage_hours,
        'Daily_Unlocks'            : data.daily_unlocks,
        'Study_Hours'              : data.study_hours,
        'Physical_Activity_Hours'  : data.physical_activity_hours,
        'Sleep_Hours_Per_Night'    : data.sleep_hours_per_night,
        'Stress_Level'             : data.stress_level,
        'Grouped_Country'          : country_group
    }])


def get_risk_level(score: float) -> str:
    if score >= 7:
        return "Healthy"
    elif score >= 5:
        return "Mild Concern"
    elif score >= 3.5:
        return "Moderate Risk"
    else:
        return "High Risk"


def get_top_factors(pipeline, top_n: int = 3) -> list[str]:
    regressor = pipeline.named_steps['regressor']
    feature_names = pipeline.named_steps['preprocessor'].get_feature_names_out()

    importance_pairs = sorted(
        zip(feature_names, regressor.feature_importances_),
        key=lambda pair: pair[1],
        reverse=True
    )

    return [name.split("__", 1)[-1].replace("_", " ") for name, _ in importance_pairs[:top_n]]


def generate_recommendations(data: StudentData) -> list[str]:
    recommendations = []

    if data.sleep_hours_per_night < 6:
        recommendations.append("Sleep 7-8 hours.")

    if data.stress_level in ['High', 'Very High']:
        recommendations.append("Practice stress management.")

    if data.avg_daily_usage_hours > 5:
        recommendations.append("Reduce social media usage.")

    if data.daily_unlocks > 100:
        recommendations.append("Reduce unnecessary phone checking.")

    if data.physical_activity_hours < 1:
        recommendations.append("Exercise regularly.")

    if data.study_hours < 2:
        recommendations.append("Improve study routine.")

    if not recommendations:
        recommendations.append("Your current lifestyle habits look well balanced. Keep it up!")

    return recommendations


@app.get('/')
def greet():
    return {
        "project": "AI Mental Health Insight & Recommendation System",
        "model": "Random Forest Regressor",
        "status": "Running"
    }


@app.post('/predict', response_model=PredictionResponse)
def predict(data: StudentData):
    try:
        input_row = build_input_row(data)
        prediction = model.predict(input_row)[0]
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to generate a prediction for the given input.")

    return PredictionResponse(predicted_mental_health_score=round(float(prediction), 2))


@app.post('/analyze', response_model=AnalysisResponse)
def analyze(data: StudentData):
    try:
        input_row = build_input_row(data)
        score = round(float(model.predict(input_row)[0]), 2)
        risk_level = get_risk_level(score)
        top_factors = get_top_factors(model)
        recommendations = generate_recommendations(data)
    except Exception:
        raise HTTPException(status_code=400, detail="Unable to analyze the given input.")

    summary = (
        f"Based on the provided lifestyle habits, the predicted mental health score is "
        f"{score}, placing this user in the '{risk_level}' category."
    )

    return AnalysisResponse(
        mental_health_score=score,
        risk_level=risk_level,
        top_factors=top_factors,
        recommendations=recommendations,
        summary=summary
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
