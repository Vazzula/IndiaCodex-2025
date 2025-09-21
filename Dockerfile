FROM ubuntu:latest
LABEL authors="vazzu"

ENTRYPOINT ["top", "-b"]