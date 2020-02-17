FROM bentheiii/pywps

COPY const/ ./const
COPY processes/ ./processes
COPY *.py ./
COPY *.cfg ./

RUN mkdir -p ./logs ./outputs ./workdir

#CMD ls
CMD ["gunicorn" ,"--bind", "0.0.0.0:80", "main:app"]