FROM bentheiii/pywps

COPY static/data/ ./static/data
COPY processes/ ./processes
COPY *.py ./
COPY *.cfg ./

RUN python3 -m pip install gdalos, czml3

RUN mkdir -p ./logs ./outputs ./workdir

#CMD ls
CMD ["gunicorn" ,"--bind", "0.0.0.0:80", "main:app"]