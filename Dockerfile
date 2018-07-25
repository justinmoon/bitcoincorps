FROM jupyter/minimal-notebook

USER root

RUN apt-get install -yq --no-install-recommends \
    python3.7 \
    vim

USER $NB_UID
