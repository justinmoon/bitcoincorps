FROM jupyter/minimal-notebook

USER root

RUN apt-get install software-properties-common

RUN add-apt-repository ppa:deadsnakes/ppa && \
    apt-get update && \
    apt-get install -yq --no-install-recommends \
    python3.7 \
    vim

USER $NB_UID
