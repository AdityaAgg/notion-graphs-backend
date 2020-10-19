FROM python:3.8-slim-buster
WORKDIR /notion_graphs_backend
ADD . /notion_graphs_backend
RUN pip install -r requirements.txt
ENTRYPOINT ["gunicorn", "wsgi:app", "-w", "2", "--threads", "2", "-b", "0.0.0.0:5000"]
