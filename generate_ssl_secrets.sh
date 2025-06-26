sudo openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout ./nginx/ssl-secrets/ssl_domain.key \
  -out ./nginx/ssl-secrets/ssl_domain_chain.crt \
  -subj "/C=US/ST=State/L=City/O=Org/OU=Dev/CN=localhost"