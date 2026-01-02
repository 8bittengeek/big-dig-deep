# Qortal build container)
FROM openjdk:11-jre-slim

WORKDIR /qortal-bdh

# Copy your built Qortal core jar + settings
COPY qortal/target/qortal-5.0.6.jar /qortal-bdh/qortal.jar
COPY qortal/testnet/settings-test.json /qortal-bdh/settings.json

EXPOSE 1234  # API port
CMD ["java", "-jar", "/qortal-bdh/qortal.jar", "settings.json"]
