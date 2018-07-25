FROM jupyter/minimal-notebook

ARG JUPYTERLAB_VERSION=0.32.1
RUN     pip install jupyterlab==$JUPYTERLAB_VERSION \
    &&  jupyter labextension install @jupyterlab/hub-extension
