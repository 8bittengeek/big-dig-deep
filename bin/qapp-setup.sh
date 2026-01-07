#!/bin/bash
TARGET=~/qapps/big-web-archive/
mkdir -p $TARGET
cp -rv qapp/* $TARGET
pushd $TARGET
zip -r big-web-archive.zip q-app.json index.html styles.css qapp.js archive/
