FROM php:8.1-apache

# Install PDO MySQL, MySQLi, and the cURL extension used by Atlas_client
RUN apt-get update && apt-get install -y --no-install-recommends libcurl4-openssl-dev \
    && docker-php-ext-install pdo pdo_mysql mysqli curl \
    && rm -rf /var/lib/apt/lists/*

# Enable Apache mod_rewrite for clean CodeIgniter routing and suppress FQDN warning
RUN a2enmod rewrite && echo "ServerName localhost" >> /etc/apache2/apache2.conf

# Copy custom Apache virtual host configuration
RUN echo '<Directory /var/www/html/>\n\
    Options Indexes FollowSymLinks\n\
    AllowOverride All\n\
    Require all granted\n\
</Directory>' > /etc/apache2/conf-available/codeigniter.conf && \
    a2enconf codeigniter

# Copy CodeIgniter 3 application source
COPY . /var/www/html/

# Ensure proper permissions
RUN chown -R www-data:www-data /var/www/html

EXPOSE 80
CMD ["apache2-foreground"]
