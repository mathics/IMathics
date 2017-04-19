FROM jupyter/base-notebook
MAINTAINER Bernhard Liebl <Bernhard.Liebl@gmx.org>

USER root

RUN apt-get update && apt-get -y install python python3 python3-pip git curl

RUN cd $HOME && git clone https://github.com/poke1024/Mathics.git && \
	cd Mathics && git checkout layoutengine && python3 setup.py install

RUN cd $HOME && git clone https://github.com/poke1024/IMathics.git && \
	cd IMathics && python3 setup.py install

RUN curl -sL https://deb.nodesource.com/setup_6.x | bash - && apt-get install -y nodejs

RUN apt-get update && apt-get -y install libzmq3-dev && npm install mathjax-node zerorpc svg2png

RUN cd $HOME && git clone https://github.com/poke1024/zerorpc-python && \
	cd zerorpc-python && git checkout python3.4 && \
	python3 setup.py install

# RUN jupyter-nbextension enable --py --sys-prefix widgetsnbextension

ENV NODE_PATH '/home/jovyan/work/node_modules/'

USER $NB_USER

RUN conda install -y ipywidgets
