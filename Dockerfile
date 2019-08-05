FROM python:3

# install debian packages
ENV DEBIAN_FRONTEND noninteractive

RUN apt-get update -qq \
    && apt-get install --no-install-recommends -y \
    # install essentials
    build-essential \
    # Boost for dlib
  	cmake \
  	libboost-all-dev \
    python3-setuptools \
    # Chinese font
    fonts-arphic-ukai \
    fontconfig \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Cache font file for access
RUN fc-cache

WORKDIR /usr/src/face_recog
COPY ./requirements.txt ./
RUN python3 -m pip --no-cache-dir install -r requirements.txt

COPY . .

ARG MODE_ENV
RUN if [ "$MODE_ENV" = "production" ]; \
	then mv ./prod_token.txt ./active_token.txt && echo "#production#" && \
       mv ./prod_root_token.txt ./active_root_token.txt && \
       mv ./model/prod_config.py ./model/config.py; \
	else mv ./dev_token.txt ./active_token.txt && echo "#development#" && \
       mv ./dev_root_token.txt ./active_root_token.txt && \
       mv ./model/test_config.py ./model/config.py; \
fi
RUN echo $MODE_ENV

CMD ["python3", "-u", "main.py"]
# CMD ["/bin/bash"]
