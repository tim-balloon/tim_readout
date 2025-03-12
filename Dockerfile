#FROM python:3.7
FROM simonsobs/ocs:v0.10.3

WORKDIR /primecam_readout

# Copy requirements and install dependencies first (cache layer)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the __init__.py file (if needed at the root)
COPY __init__.py /

# Copy the src directory last (frequent changes)
COPY ./src ./src/

# ENTRYPOINT and CMD remain the same
ENTRYPOINT ["dumb-init", "ocs-agent-cli"]
CMD ["--agent", "src/queen_agent.py", "--entrypoint", "main"]




# FROM simonsobs/ocs:v0.10.3

# WORKDIR /primecam_readout

# COPY requirements.txt .
# COPY ./src .
# COPY __init__.py /

# RUN pip install -r requirements.txt

# # CMD ["python", "./primecam_readout/queen_agent.py"]

# ENTRYPOINT ["dumb-init", "ocs-agent-cli"]
# CMD ["--agent", "queen_agent.py", "--entrypoint", "main"]