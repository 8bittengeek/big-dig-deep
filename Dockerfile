# Qortal build container
FROM eclipse-temurin:11-jre


WORKDIR /qortal-bdd

# Copy your built Qortal core jar + settings
COPY qortal.jar /qortal-bdd/qortal.jar
COPY qortal-testnet-settings.json /qortal-bdd/settings.json

# EXPOSE 62392  # API port
CMD ["java", "-jar", "/qortal-bdd/qortal.jar", "settings.json"]
