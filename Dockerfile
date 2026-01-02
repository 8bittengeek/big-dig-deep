# Qortal build container
FROM eclipse-temurin:11-jre


WORKDIR /qortal-bdh

# Copy your built Qortal core jar + settings
COPY qortal.jar /qortal-bdh/qortal.jar
COPY qortal-testnet-settings.json /qortal-bdh/settings.json

# EXPOSE 62392  # API port
CMD ["java", "-jar", "/qortal-bdh/qortal.jar", "settings.json"]
