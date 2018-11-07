FROM continuumio/miniconda3
RUN conda create -n crds-env --yes -c http://ssb.stsci.edu/conda-dev stsci jwst python=3.6
RUN conda remove --force -n crds-env crds
RUN git clone https://github.com/spacetelescope/crds.git CRDS
RUN echo "source activate crds-env" > ~/.bashrc
ENV PATH /opt/conda/envs/crds-env/bin:$PATH
RUN cd CRDS && ./install


