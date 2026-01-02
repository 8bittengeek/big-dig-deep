# Qortal build container)
FROM openjdk:11-jre-slim

WORKDIR /qortal

# Copy your built Qortal core jar + settings
COPY qortal/target/qortal-5.0.6.jar /qortal/qortal.jar
COPY qortal/testnet/settings-test.json /qortal/settings.json

EXPOSE 1234  # API port
CMD ["java", "-jar", "/qortal/qortal.jar", "settings.json"]
