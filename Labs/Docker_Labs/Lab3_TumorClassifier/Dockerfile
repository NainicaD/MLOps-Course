# ---------- Stage 1: train the model ----------
FROM python:3.11-slim AS model_training
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/model_training.py .
RUN python model_training.py

# ---------- Stage 2: serve the model ----------
FROM python:3.11-slim AS serving
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Only the trained model is carried over from Stage 1, not the training script
COPY --from=model_training /app/tumor_model.joblib .
COPY src/main.py .
COPY src/templates ./templates
COPY src/statics ./statics
EXPOSE 4000
CMD ["python", "main.py"]
