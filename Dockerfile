#********************************************************************************
#          ___  _     _ _                  _                 _                  *
#         / _ \| |   (_) |                | |               | |                 *
#        | (_) | |__  _| |_ __ _  ___  ___| | __  _ __   ___| |_                *
#         > _ <| '_ \| | __/ _` |/ _ \/ _ \ |/ / | '_ \ / _ \ __|               *
#        | (_) | |_) | | || (_| |  __/  __/   < _| | | |  __/ |_                *
#         \___/|_.__/|_|\__\__, |\___|\___|_|\_(_)_| |_|\___|\__|               *
#                           __/ |                                               *
#                          |___/                                                *
#                                                                               *
#*******************************************************************************/

# Qortal build container
FROM eclipse-temurin:11-jdk

WORKDIR /qortal
COPY assets/qortal.jar /qortal/qortal.jar
COPY assets/qortal-testnet-settings.json /qortal/settings.json
COPY assets/testchain.json /qortal/testchain.json

RUN mkdir -p /qortal/db-testnet /qortal/data /qortal/tmp \
    && chmod -R 777 /qortal

EXPOSE 62388  # Hub
EXPOSE 62391  # P2P
EXPOSE 62392  # API

CMD ["java",
     "-Djava.awt.headless=true",
     "-Djava.security.egd=file:/dev/./urandom",
     "-XX:MetaspaceSize=256m",
     "-XX:MaxMetaspaceSize=1g",
     "-jar", "/qortal/qortal.jar",
     "/qortal/settings.json"]
     
