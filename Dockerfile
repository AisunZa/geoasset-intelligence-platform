FROM condaforge/miniforge3:latest

WORKDIR /app

COPY api ./api

RUN conda install -y \
    -c conda-forge \
    --override-channels \
    python=3.13 \
    fastapi \
    uvicorn \
    sqlalchemy \
    psycopg \
    && conda clean -afy

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]