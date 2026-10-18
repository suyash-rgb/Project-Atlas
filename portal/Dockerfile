FROM php:8.1-apache

# Install PDO MySQL and cURL extensions
RUN docker-php-ext-install pdo pdo_mysql mysqli

# Enable Apache mod_rewrite for clean CodeIgniter routing
RUN a2enmod rewrite

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
