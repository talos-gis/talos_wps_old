#FROM osgeo/gdal:latest
FROM osgeo/gdal:ubuntu-small-latest

# ENV WORKDIR=/usr/src/app
ENV WORKDIR=/app

RUN apt-get install -y --no-install-recommends python3-distutils python3-pip python3-setuptools python3-wheel
COPY requirements.txt ./
RUN python3 -m pip install -r requirements.txt

RUN echo this line is here so that docker will rerun the following commands not from cache: #4

RUN python3 -m pip install --index-url https://test.pypi.org/simple/ --upgrade gdalos

WORKDIR ${WORKDIR}
COPY ./src ./src
COPY ./data/sample ./data/sample
COPY ./data/static/config ./static/config

COPY src/patch/core.py /usr/local/lib/python3.8/dist-packages/czml3/

RUN mkdir -p ./logs ./outputs ./workdir ./data/static/maps

CMD gunicorn --bind 0.0.0.0:5000 --chdir ${WORKDIR}/src main:app