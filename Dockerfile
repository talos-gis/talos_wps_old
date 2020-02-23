ARG STATIC_DIR="const/"
FROM bentheiii/pywps

ENV STATIC_DIR=$STATIC_DIR

COPY ${STATIC_DIR} ./const
COPY processes/ ./processes
COPY *.py ./
COPY *.cfg ./

RUN mkdir -p ./logs ./outputs ./workdir

#CMD ls
CMD ["gunicorn" ,"--bind", "0.0.0.0:80", "main:app"]