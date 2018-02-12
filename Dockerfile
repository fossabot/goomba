FROM alpine

RUN apk update && apk add python3

COPY ./ /tmp/goomba
RUN cd /tmp/goomba && \
    pip install -r requirements.txt && \
    pip install .

ENTRYPOINT ["goomba"]
CMD ["config.yaml"]
