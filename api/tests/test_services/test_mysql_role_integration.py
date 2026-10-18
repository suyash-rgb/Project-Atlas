import os

import mysql.connector
import pytest


pytestmark = pytest.mark.skipif(
    os.getenv("ATLAS_MYSQL_INTEGRATION_TESTS") != "1",
    reason="Set ATLAS_MYSQL_INTEGRATION_TESTS=1 to run against a dedicated MySQL test database.",
)


def test_readonly_database_user_can_select_but_cannot_write():
    required = (
        "ATLAS_MYSQL_TEST_HOST",
        "ATLAS_MYSQL_TEST_DATABASE",
        "ATLAS_MYSQL_TEST_READONLY_USER",
        "ATLAS_MYSQL_TEST_READONLY_PASSWORD",
    )
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        pytest.fail(f"Missing MySQL integration settings: {', '.join(missing)}")

    connection = mysql.connector.connect(
        host=os.environ["ATLAS_MYSQL_TEST_HOST"],
        port=int(os.getenv("ATLAS_MYSQL_TEST_PORT", "3306")),
        database=os.environ["ATLAS_MYSQL_TEST_DATABASE"],
        user=os.environ["ATLAS_MYSQL_TEST_READONLY_USER"],
        password=os.environ["ATLAS_MYSQL_TEST_READONLY_PASSWORD"],
        autocommit=False,
    )
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT 1")
        assert cursor.fetchone() == (1,)

        with pytest.raises(mysql.connector.Error) as error:
            cursor.execute("UPDATE feedback SET rating = rating WHERE 1 = 0")
        assert error.value.errno == 1142
    finally:
        connection.rollback()
        cursor.close()
        connection.close()
