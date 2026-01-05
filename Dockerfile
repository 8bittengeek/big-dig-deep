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
FROM eclipse-temurin:11-jre

WORKDIR /qortal-bdd

# Copy your built Qortal core jar + settings
COPY assets/qortal.jar /qortal-bdd/qortal.jar
COPY assets/qortal-testnet-settings.json /qortal-bdd/settings.json
COPY assets/testchain.json /qortal-bdd/testchain.json

# EXPOSE 62392  # API port
CMD ["java", "-jar", "/qortal-bdd/qortal.jar", "settings.json"]
