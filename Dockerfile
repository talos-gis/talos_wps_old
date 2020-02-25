FROM osgeo/gdal:latest

# ENV WORKDIR=/usr/src/app
ENV WORKDIR=/app
# ENV DATA_DIR "/data"

RUN apt-get install -y --no-install-recommends python3-distutils python3-pip python3-setuptools python3-wheel
RUN python3 -m pip install flask gunicorn pywps gdalos czml3

WORKDIR ${WORKDIR}
COPY static/ ./static
COPY processes/ ./processes
COPY *.py ./
COPY *.cfg ./

RUN mkdir -p ./logs ./outputs ./workdir ./static/data

#CMD ls
CMD ["gunicorn" ,"--bind", "0.0.0.0:5000", "main:app"]