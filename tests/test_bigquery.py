# encoding: utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Author: Kyle Lahnakoski (kyle@lahnakoski.com)
#

from __future__ import absolute_import, division, unicode_literals

from unittest import TestCase, skip

from mo_parsing.debug import Debugger
from mo_testing.fuzzytestcase import FuzzyTestCase

from mo_sql_parsing import parse_bigquery as parse


class TestBigQuery(TestCase):
    def test_with_expression(self):
        # https://github.com/pyparsing/pyparsing/issues/291
        sql = """with t as (CASE EXTRACT(dayofweek FROM CURRENT_DATETIME()) when 1 then "S" end) select * from t"""
        result = parse(sql)
        expected = {
            "from": "t",
            "select": "*",
            "with": {
                "name": "t",
                "value": {"case": {
                    "then": {"literal": "S"},
                    "when": {"eq": [{"extract": ["dow", {"current_datetime": {}}]}, 1]},
                }},
            },
        }
        self.assertEqual(result, expected)

    def testA(self):
        sql = """SELECT FIRST_VALUE(finish_time) OVER w1 AS fastest_time"""
        result = parse(sql)
        expected = {"select": {
            "name": "fastest_time",
            "over": "w1",
            "value": {"first_value": "finish_time"},
        }}
        self.assertEqual(result, expected)

    def testB(self):
        sql = """
          SELECT 
            name,
            FIRST_VALUE(finish_time) OVER w1 AS fastest_time,
            NTH_VALUE(finish_time, 2) OVER w1 as second_fastest
          FROM finishers
          WINDOW w1 AS (
            PARTITION BY division ORDER BY finish_time ASC
            ROWS BETWEEN UNBOUNDED PRECEDING AND UNBOUNDED FOLLOWING
          )
        """
        result = parse(sql)
        expected = {
            "from": [
                "finishers",
                {"window": {
                    "name": "w1",
                    "value": {
                        "orderby": {"sort": "asc", "value": "finish_time"},
                        "partitionby": "division",
                        "range": {},
                    },
                }},
            ],
            "select": [
                {"value": "name"},
                {
                    "name": "fastest_time",
                    "over": "w1",
                    "value": {"first_value": "finish_time"},
                },
                {
                    "name": "second_fastest",
                    "over": "w1",
                    "value": {"nth_value": ["finish_time", 2]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def testF(self):
        sql = """
            SELECT
              PERCENTILE_CONT(x, 0) OVER() AS min,
              PERCENTILE_CONT(x, 0.01) OVER() AS percentile1,
              PERCENTILE_CONT(x, 0.5) OVER() AS median,
              PERCENTILE_CONT(x, 0.9) OVER() AS percentile90,
              PERCENTILE_CONT(x, 1) OVER() AS max
            FROM UNNEST([0, 3, NULL, 1, 2]) AS x LIMIT 1
            """
        result = parse(sql)
        expected = {
            "from": {
                "name": "x",
                "value": {"unnest": {"create_array": [0, 3, {"null": {}}, 1, 2]}},
            },
            "limit": 1,
            "select": [
                {"name": "min", "over": {}, "value": {"percentile_cont": ["x", 0]}},
                {
                    "name": "percentile1",
                    "over": {},
                    "value": {"percentile_cont": ["x", 0.01]},
                },
                {
                    "name": "median",
                    "over": {},
                    "value": {"percentile_cont": ["x", 0.5]},
                },
                {
                    "name": "percentile90",
                    "over": {},
                    "value": {"percentile_cont": ["x", 0.9]},
                },
                {"name": "max", "over": {}, "value": {"percentile_cont": ["x", 1]}},
            ],
        }
        self.assertEqual(result, expected)

    def testG(self):
        sql = """
               SELECT
                 x,
                 PERCENTILE_DISC(x, 0) OVER() AS min,
                 PERCENTILE_DISC(x, 0.5) OVER() AS median,
                 PERCENTILE_DISC(x, 1) OVER() AS max
               FROM UNNEST(['c', NULL, 'b', 'a']) AS x
               """
        result = parse(sql)
        expected = {
            "from": {
                "name": "x",
                "value": {"unnest": {"create_array": [
                    {"literal": "c"},
                    {"null": {}},
                    {"literal": "b"},
                    {"literal": "a"},
                ]}},
            },
            "select": [
                {"value": "x"},
                {"name": "min", "over": {}, "value": {"percentile_disc": ["x", 0]}},
                {
                    "name": "median",
                    "over": {},
                    "value": {"percentile_disc": ["x", 0.5]},
                },
                {"name": "max", "over": {}, "value": {"percentile_disc": ["x", 1]}},
            ],
        }

        self.assertEqual(result, expected)

    def testL(self):
        sql = """SELECT PERCENTILE_DISC(x, 0) OVER() AS min"""
        result = parse(sql)
        expected = {"select": {
            "name": "min",
            "value": {"percentile_disc": ["x", 0]},
            "over": {},
        }}
        self.assertEqual(result, expected)

    def testI(self):
        sql = """
            WITH date_hour_slots AS (
             SELECT
                [
                    STRUCT(
                        " 00:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01', current_date(), INTERVAL 1 DAY) as dt_range
                    ),
                    STRUCT(
                        " 01:00:00 UTC" as hrs,
                        GENERATE_DATE_ARRAY('2016-01-01',current_date(), INTERVAL 1 DAY) as dt_range
                    )
                ] AS full_timestamps
            )
            SELECT
                dt AS dates, 
                hrs, 
                CAST(CONCAT( CAST(dt as STRING), CAST(hrs as STRING)) as TIMESTAMP) as timestamp_value
            FROM 
                `date_hour_slots`, 
                date_hour_slots.full_timestamps 
            LEFT JOIN 
                full_timestamps.dt_range as dt
            """
        result = parse(sql)
        expected = {
            "from": [
                "date_hour_slots",
                "date_hour_slots.full_timestamps",
                {"left join": {"name": "dt", "value": "full_timestamps.dt_range"}},
            ],
            "select": [
                {"name": "dates", "value": "dt"},
                {"value": "hrs"},
                {
                    "name": "timestamp_value",
                    "value": {"cast": [
                        {"concat": [
                            {"cast": ["dt", {"string": {}}]},
                            {"cast": ["hrs", {"string": {}}]},
                        ]},
                        {"timestamp": {}},
                    ]},
                },
            ],
            "with": {
                "name": "date_hour_slots",
                "value": {"select": {
                    "name": "full_timestamps",
                    "value": {"create_array": [
                        {"create_struct": [
                            {"name": "hrs", "value": {"literal": " 00:00:00 UTC"}},
                            {
                                "name": "dt_range",
                                "value": {"generate_date_array": [
                                    {"literal": "2016-01-01"},
                                    {"current_date": {}},
                                    {"interval": [1, "day"]},
                                ]},
                            },
                        ]},
                        {"create_struct": [
                            {"name": "hrs", "value": {"literal": " 01:00:00 UTC"}},
                            {
                                "name": "dt_range",
                                "value": {"generate_date_array": [
                                    {"literal": "2016-01-01"},
                                    {"current_date": {}},
                                    {"interval": [1, "day"]},
                                ]},
                            },
                        ]},
                    ]},
                }},
            },
        }
        self.assertEqual(result, expected)

    def testH(self):
        sql = """
            SELECT
                -- [foo],
                ARRAY[foo],
                -- ARRAY<int64, STRING>[foo, bar],  INVALID
                ARRAY<STRING>[foo, bar],
                STRUCT(1, 3),
                STRUCT<int64, STRING>(2, 'foo')
            FROM
                T
            """
        result = parse(sql)
        expected = {
            "from": "T",
            "select": [
                {"value": {"create_array": "foo"}},
                {"value": {"cast": [
                    {"create_array": ["foo", "bar"]},
                    {"array": {"string": {}}},
                ]}},
                {"value": {"create_struct": [1, 3]}},
                {"value": {"cast": [
                    {"create_struct": [2, {"literal": "foo"}]},
                    {"struct": [{"int64": {}}, {"string": {}}]},
                ]}},
            ],
        }

        self.assertEqual(result, expected)

    def testK(self):
        sql = """
            SELECT
                STRUCT<int64, STRING>(2, 'foo')
            """
        result = parse(sql)
        expected = {"select": {"value": {"cast": [
            {"create_struct": [2, {"literal": "foo"}]},
            {"struct": [{"int64": {}}, {"string": {}}]},
        ]}}}

        self.assertEqual(result, expected)

    def testJ(self):
        sql = """
            SELECT
                current_date(),
                GENERATE_ARRAY(5, NULL, 1),
                GENERATE_DATE_ARRAY('2016-10-05', '2016-10-01', INTERVAL 1 DAY),
                GENERATE_DATE_ARRAY('2016-10-05', NULL),
                GENERATE_DATE_ARRAY('2016-01-01', '2016-12-31', INTERVAL 2 MONTH),
                GENERATE_DATE_ARRAY('2000-02-01',current_date(), INTERVAL 1 DAY),
                GENERATE_TIMESTAMP_ARRAY('2016-10-05 00:00:00', '2016-10-05 00:00:02', INTERVAL 1 SECOND)
            FROM
                bar
            """
        result = parse(sql)
        expected = {
            "from": "bar",
            "select": [
                {"value": {"current_date": {}}},
                {"value": {"generate_array": [5, {"null": {}}, 1]}},
                {"value": {"generate_date_array": [
                    {"literal": "2016-10-05"},
                    {"literal": "2016-10-01"},
                    {"interval": [1, "day"]},
                ]}},
                {"value": {"generate_date_array": [
                    {"literal": "2016-10-05"},
                    {"null": {}},
                ]}},
                {"value": {"generate_date_array": [
                    {"literal": "2016-01-01"},
                    {"literal": "2016-12-31"},
                    {"interval": [2, "month"]},
                ]}},
                {"value": {"generate_date_array": [
                    {"literal": "2000-02-01"},
                    {"current_date": {}},
                    {"interval": [1, "day"]},
                ]}},
                {"value": {"generate_timestamp_array": [
                    {"literal": "2016-10-05 00:00:00"},
                    {"literal": "2016-10-05 00:00:02"},
                    {"interval": [1, "second"]},
                ]}},
            ],
        }
        self.assertEqual(result, expected)

    def testN(self):
        sql = """
            SELECT DATE_SUB(current_date("-08:00"), INTERVAL 2 DAY)
            """
        result = parse(sql)
        expected = {"select": {"value": {"date_sub": [
            {"current_date": {"literal": "-08:00"}},
            {"interval": [2, "day"]},
        ]}}}
        self.assertEqual(result, expected)

    def testQ(self):
        sql = """
            WITH a AS (
                SELECT b FROM c
                UNION ALL
                (
                    WITH d AS (
                        SELECT e FROM f
                    )
                    SELECT g FROM d
                )
            )
            SELECT h FROM a
            """
        result = parse(sql)
        expected = {
            "from": "a",
            "select": {"value": "h"},
            "with": {
                "name": "a",
                "value": {"union_all": [
                    {"from": "c", "select": {"value": "b"}},
                    {
                        "from": "d",
                        "select": {"value": "g"},
                        "with": {
                            "name": "d",
                            "value": {"from": "f", "select": {"value": "e"}},
                        },
                    },
                ]},
            },
        }
        self.assertEqual(result, expected)

    def testU(self):
        sql = """SELECT  * FROM `a`.b.`c`"""
        result = parse(sql)
        expected = {"from": "a.b.c", "select": "*"}
        self.assertEqual(result, expected)

    def testV(self):
        sql = """SELECT * FROM `a.b.c` a1
                JOIN `a.b.d` a2
                    ON cast(a1.field AS BIGDECIMAL) = cast(a2.field AS BIGNUMERIC)"""
        result = parse(sql)
        expected = {
            "select": "*",
            "from": [
                {"value": "a..b..c", "name": "a1"},
                {
                    "join": {"value": "a..b..d", "name": "a2"},
                    "on": {"eq": [
                        {"cast": ["a1.field", {"bigdecimal": {}}]},
                        {"cast": ["a2.field", {"bignumeric": {}}]},
                    ]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def testW(self):
        sql = """SELECT * FROM `a.b.c` a1
                JOIN `a.b.d` a2
                    ON cast(a1.field AS INT64) = cast(a2.field AS BYTEINT)"""
        result = parse(sql)
        expected = {
            "select": "*",
            "from": [
                {"value": "a..b..c", "name": "a1"},
                {
                    "join": {"value": "a..b..d", "name": "a2"},
                    "on": {"eq": [
                        {"cast": ["a1.field", {"int64": {}}]},
                        {"cast": ["a2.field", {"byteint": {}}]},
                    ]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def testS(self):
        sql = """
            SELECT * FROM 'a'.b.`c`
            """
        with FuzzyTestCase.assertRaises(
            """'a'.b.`c`" (at char 27), (line:2, col:27)"""
        ):
            parse(sql)

    def test_issue_96_r_expressions1(self):
        result = parse("SELECT regex_extract(x, r'[a-z]'), value FROM `a.b.c`")
        expected = {
            "from": "a..b..c",
            "select": [
                {"value": {"regex_extract": ["x", {"regex": "[a-z]"}]}},
                {"value": "value"},
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_96_r_expressions2(self):
        result = parse('SELECT regex_extract(x, r"[a-z]"), value FROM `a.b.c`')
        expected = {
            "from": "a..b..c",
            "select": [
                {"value": {"regex_extract": ["x", {"regex": "[a-z]"}]}},
                {"value": "value"},
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_97_safe_cast(self):
        result = parse("SELECT SAFE_CAST(x AS STRING) from `a.b.c`")
        expected = {
            "from": "a..b..c",
            "select": {"value": {"safe_cast": ["x", {"string": {}}]}},
        }
        self.assertEqual(result, expected)

    def test_issue_98_interval1(self):
        result = parse(
            """SELECT timestamp_add('2022-07-14T12:42:11Z', INTERVAL x MINUTE)"""
        )
        expected = {"select": {"value": {"timestamp_add": [
            {"literal": "2022-07-14T12:42:11Z"},
            {"interval": ["x", "minute"]},
        ]}}}
        self.assertEqual(result, expected)

    @skip("missing FROM?")
    def test_issue_98_interval2(self):
        result = parse(
            """SELECT timestamp_add('2022-07-14T12:42:11Z', INTERVAL x MINUTE) UNNEST(GENERATE_ARRAY(1, 10)) as x"""
        )
        expected = {}
        self.assertEqual(result, expected)

    def test_issue_99_select_except(self):
        result = parse("SELECT * EXCEPT(x) FROM `a.b.c`")
        expected = {"from": "a..b..c", "select_except": {"value": "x"}}
        self.assertEqual(result, expected)

    def test_unnest(self):
        result = parse(
            """SELECT * FROM UNNEST([1, 2, 2, 5, NULL]) AS unnest_column WITH OFFSET AS `offset`"""
        )
        expected = {
            "select": "*",
            "from": {
                "name": "unnest_column",
                "value": {"unnest": {"create_array": [1, 2, 2, 5, {"null": {}}]}},
                "with_offset": "offset",
            },
        }
        self.assertEqual(result, expected)

    def test_issue_123_declare1(self):
        sql = """DECLARE _current_timestamp timestamp DEFAULT current_timestamp();"""
        result = parse(sql)
        expected = {"declare": {
            "name": "_current_timestamp",
            "type": {"timestamp": {}},
            "default": {"current_timestamp": {}},
        }}
        self.assertEqual(result, expected)

    def test_issue_123_declare2(self):
        sql = """DECLARE _current_date      date      DEFAULT current_date("America/Sao_Paulo");"""
        result = parse(sql)
        expected = {"declare": {
            "name": "_current_date",
            "type": {"date": {}},
            "default": {"current_date": {"literal": "America/Sao_Paulo"}},
        }}
        self.assertEqual(result, expected)

    def test_issue_141_string_agg(self):
        sql = """
            SELECT 
                string_agg(address_type.name, ', ') as address_type_name
                ,string_agg(address.street order by length(address.street) limit 1) as street 
                ,string_agg(address.complement order by length(address.complement) limit 1) as complement 
        """
        result = parse(sql)
        expected = {"select": [
            {
                "name": "address_type_name",
                "value": {"string_agg": ["address_type.name", {"literal": ", "}]},
            },
            {
                "name": "street",
                "value": {
                    "limit": 1,
                    "orderby": {"value": {"length": "address.street"}},
                    "string_agg": "address.street",
                },
            },
            {
                "name": "complement",
                "value": {
                    "limit": 1,
                    "orderby": {"value": {"length": "address.complement"}},
                    "string_agg": "address.complement",
                },
            },
        ]}
        self.assertEqual(result, expected)

    def test_issue_142_array_agg(self):
        sql = """SELECT ARRAY_AGG(DISTINCT email IGNORE NULLS) AS email"""
        result = parse(sql)
        expect = {"select": {
            "name": "email",
            "value": {"array_agg": "email", "distinct": True, "nulls": "ignore"},
        }}
        self.assertEqual(result, expect)

    def test_issue_145(self):
        sql = """WITH
            shift_history_pivoted as (
                SELECT * FROM `*********************.**************.**************` 
                    UNPIVOT INCLUDE NULLS (
                        status FOR time_interval IN (
                            x0h00m_0h30m,
                            x0h30m_1h00m
                        )
                    )
            )            
            SELECT
                id
            FROM
                nu_com_a_mao_no_bolso
            WHERE
                time_interval IS NOT NULL
            """
        result = parse(sql)
        expected = {
            "select": {"value": "id"},
            "from": "nu_com_a_mao_no_bolso",
            "where": {"exists": "time_interval"},
            "with": {
                "name": "shift_history_pivoted",
                "value": {
                    "select": "*",
                    "from": [
                        "*********************..**************..**************",
                        {"unpivot": {
                            "for": "time_interval",
                            "in": {"value": ["x0h00m_0h30m", "x0h30m_1h00m"]},
                            "nulls": True,
                            "value": "status",
                        }},
                    ],
                },
            },
        }

        self.assertEqual(result, expected)

    def test_issue_150(self):
        sql = """SELECT AS STRUCT
            CASE
                WHEN ee.babala = TRUE THEN 'avisos'
                ELSE NULL
            END AS bot_name,
            ee.avisos AS estagio,
            SAFE_CAST(NULL AS STRING) AS demanda,
            SAFE_CAST(NULL AS STRING) AS transfere,
            SAFE_CAST(NULL AS STRING) AS segurana,
            SAFE_CAST(NULL AS BOOLEAN) AS jacson"""
        result = parse(sql)
        expected = {"select_as_struct": [
            {
                "name": "bot_name",
                "value": {"case": [
                    {
                        "then": {"literal": "avisos"},
                        "when": {"eq": ["ee.babala", True]},
                    },
                    {"null": {}},
                ]},
            },
            {"name": "estagio", "value": "ee.avisos"},
            {"name": "demanda", "value": {"safe_cast": [{"null": {}}, {"string": {}}]}},
            {
                "name": "transfere",
                "value": {"safe_cast": [{"null": {}}, {"string": {}}]},
            },
            {
                "name": "segurana",
                "value": {"safe_cast": [{"null": {}}, {"string": {}}]},
            },
            {"name": "jacson", "value": {"safe_cast": [{"null": {}}, {"boolean": {}}]}},
        ]}
        self.assertEqual(result, expected)

    def test_issue_155_trailing_comma(self):
        sql = """SELECT
            a.day AS src,
            b.day as tgt,
            ROW_NUMBER() OVER(PARTITION BY a.day ORDER BY b.day) - 1 AS qtde_wd,
        FROM workdays a
        join workdays b ON a.day <= b.day"""
        result = parse(sql)
        expected = {
            "from": [
                {"name": "a", "value": "workdays"},
                {
                    "join": {"name": "b", "value": "workdays"},
                    "on": {"lte": ["a.day", "b.day"]},
                },
            ],
            "select": [
                {"name": "src", "value": "a.day"},
                {"name": "tgt", "value": "b.day"},
                {
                    "name": "qtde_wd",
                    "value": {"sub": [
                        {
                            "over": {
                                "orderby": {"value": "b.day"},
                                "partitionby": "a.day",
                            },
                            "value": {"row_number": {}},
                        },
                        1,
                    ]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_162_extract_from(self):
        result = parse(
            """SELECT
             FORMAT_DATETIME("%Y%m%d", DATETIME(full_date)) AS date_key,
             full_date, 
             FORMAT_DATETIME("%Y/%m/%d", DATETIME(full_date)) AS date_name,
             EXTRACT(dayofweek FROM full_date) AS day_of_week,
             CASE FORMAT_DATE('%A', date(full_date))
                 WHEN 'Sunday' THEN 'Domingo'
                 WHEN 'Monday' THEN 'Segunda-feira'
                 WHEN 'Tuesday' THEN 'Terça-feira'
                 WHEN 'Wednesday' THEN 'Quarta-feira'
                 WHEN 'Thursday' THEN 'Quinta-feira'
                 WHEN 'Friday' THEN 'Sexta-feira'
                 WHEN 'Saturday' THEN 'Sábado'
             END AS day_name_of_week,
             FORMAT_DATETIME("%d", DATETIME(full_date)) AS day_of_month,
             EXTRACT(dayofyear FROM full_date) AS day_of_year,
             CASE FORMAT_DATE('%A', DATE(full_date))
                 WHEN 'Saturday' THEN 'Final de Semana'
                 WHEN 'Sunday' THEN 'Final de Semana'
                 else 'Dia da Semana'
             END AS weekday_weekend,
             EXTRACT(week FROM full_date) + 1 AS week_of_year,
             CASE FORMAT_DATETIME("%B", DATETIME(full_date))
                 WHEN 'January' THEN 'Janeiro'
                 WHEN 'February' THEN 'Fevereiro'
                 WHEN 'March' THEN 'Março'
                 WHEN 'April' THEN 'Abril'
                 WHEN 'May' THEN 'Maio'
                 WHEN 'June' THEN 'Junho'
                 WHEN 'July' THEN 'Julho'
                 WHEN 'August' THEN 'Agosto'
                 WHEN 'September' THEN 'Setembro'
                 WHEN 'October' THEN 'Outubro'
                 WHEN 'November' THEN 'Novembro'
                 WHEN 'December' THEN 'Dezembro'
             END AS month_name,
             EXTRACT(month FROM full_date) AS month_of_year,
             IF(DATE_SUB(DATE_TRUNC(DATE_ADD(full_date, INTERVAL 1 MONTH), MONTH), INTERVAL 1 DAY) = full_date, 'Y', 'N') AS is_last_day_of_month,
             EXTRACT(quarter FROM full_date) AS calendar_quarter,
             EXTRACT(year FROM full_date) AS calendar_year,
             FORMAT_DATETIME("%Y-%m", DATETIME(full_date)) AS calendar_year_month,
             concat( EXTRACT(year FROM full_date), 'Q', EXTRACT(quarter FROM full_date)) AS calendar_year_qtr,
             20170921 AS insert_audit_key,
             20170921 AS update_audit_key,
             if(full_date = holiday.date, 1, 0) AS is_national_holiday,
             1 AS filter,
             DATE_SUB(DATE_TRUNC(DATE_ADD(full_date, INTERVAL 1 month), month), INTERVAL 1 DAY) AS last_day_of_month,
             FORMAT_DATETIME("%Y%m%d", DATETIME(DATE_SUB(DATE_TRUNC(DATE_ADD(full_date, INTERVAL 1 month), month), INTERVAL 1 DAY))) AS last_day_of_month_key,
             DATE_TRUNC(full_date, month) AS first_day_of_month,
             FORMAT_DATETIME("%Y%m%d", DATETIME(DATE_TRUNC(full_date, month))) AS first_day_of_month_key
        FROM UNNEST(GENERATE_DATE_ARRAY("2000-01-01", DATE_ADD(LAST_DAY(current_date, YEAR), INTERVAL 5 YEAR), INTERVAL 1 day)) AS full_date
        LEFT 
        JOIN financial_holiday holiday     
          ON holiday.date = full_date"""
        )
        expected = {
            "select": [
                {
                    "value": {"format_datetime": [
                        {"literal": "%Y%m%d"},
                        {"datetime": "full_date"},
                    ]},
                    "name": "date_key",
                },
                {"value": "full_date"},
                {
                    "value": {"format_datetime": [
                        {"literal": "%Y/%m/%d"},
                        {"datetime": "full_date"},
                    ]},
                    "name": "date_name",
                },
                {"value": {"extract": ["dow", "full_date"]}, "name": "day_of_week"},
                {
                    "value": {"case": [
                        {
                            "then": {"literal": "Domingo"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Sunday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Segunda-feira"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Monday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Terça-feira"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Tuesday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Quarta-feira"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Wednesday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Quinta-feira"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Thursday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Sexta-feira"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Friday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Sábado"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Saturday"},
                            ]},
                        },
                    ]},
                    "name": "day_name_of_week",
                },
                {
                    "value": {"format_datetime": [
                        {"literal": "%d"},
                        {"datetime": "full_date"},
                    ]},
                    "name": "day_of_month",
                },
                {"value": {"extract": ["doy", "full_date"]}, "name": "day_of_year"},
                {
                    "value": {"case": [
                        {
                            "then": {"literal": "Final de Semana"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Saturday"},
                            ]},
                        },
                        {
                            "then": {"literal": "Final de Semana"},
                            "when": {"eq": [
                                {"format_date": [
                                    {"literal": "%A"},
                                    {"date": "full_date"},
                                ]},
                                {"literal": "Sunday"},
                            ]},
                        },
                        {"literal": "Dia da Semana"},
                    ]},
                    "name": "weekday_weekend",
                },
                {
                    "value": {"add": [{"extract": ["week", "full_date"]}, 1]},
                    "name": "week_of_year",
                },
                {
                    "value": {"case": [
                        {
                            "then": {"literal": "Janeiro"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "January"},
                            ]},
                        },
                        {
                            "then": {"literal": "Fevereiro"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "February"},
                            ]},
                        },
                        {
                            "then": {"literal": "Março"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "March"},
                            ]},
                        },
                        {
                            "then": {"literal": "Abril"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "April"},
                            ]},
                        },
                        {
                            "then": {"literal": "Maio"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "May"},
                            ]},
                        },
                        {
                            "then": {"literal": "Junho"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "June"},
                            ]},
                        },
                        {
                            "then": {"literal": "Julho"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "July"},
                            ]},
                        },
                        {
                            "then": {"literal": "Agosto"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "August"},
                            ]},
                        },
                        {
                            "then": {"literal": "Setembro"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "September"},
                            ]},
                        },
                        {
                            "then": {"literal": "Outubro"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "October"},
                            ]},
                        },
                        {
                            "then": {"literal": "Novembro"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "November"},
                            ]},
                        },
                        {
                            "then": {"literal": "Dezembro"},
                            "when": {"eq": [
                                {"format_datetime": [
                                    {"literal": "%B"},
                                    {"datetime": "full_date"},
                                ]},
                                {"literal": "December"},
                            ]},
                        },
                    ]},
                    "name": "month_name",
                },
                {"value": {"extract": ["month", "full_date"]}, "name": "month_of_year"},
                {
                    "value": {"if": [
                        {"eq": [
                            {"date_sub": [
                                {"date_trunc": [
                                    {"date_add": [
                                        "full_date",
                                        {"interval": [1, "month"]},
                                    ]},
                                    "MONTH",
                                ]},
                                {"interval": [1, "day"]},
                            ]},
                            "full_date",
                        ]},
                        {"literal": "Y"},
                        {"literal": "N"},
                    ]},
                    "name": "is_last_day_of_month",
                },
                {
                    "value": {"extract": ["quarter", "full_date"]},
                    "name": "calendar_quarter",
                },
                {"value": {"extract": ["year", "full_date"]}, "name": "calendar_year"},
                {
                    "value": {"format_datetime": [
                        {"literal": "%Y-%m"},
                        {"datetime": "full_date"},
                    ]},
                    "name": "calendar_year_month",
                },
                {
                    "value": {"concat": [
                        {"extract": ["year", "full_date"]},
                        {"literal": "Q"},
                        {"extract": ["quarter", "full_date"]},
                    ]},
                    "name": "calendar_year_qtr",
                },
                {"value": 20170921, "name": "insert_audit_key"},
                {"value": 20170921, "name": "update_audit_key"},
                {
                    "value": {"if": [{"eq": ["full_date", "holiday.date"]}, 1, 0]},
                    "name": "is_national_holiday",
                },
                {"value": 1, "name": "filter"},
                {
                    "value": {"date_sub": [
                        {"date_trunc": [
                            {"date_add": ["full_date", {"interval": [1, "month"]}]},
                            "month",
                        ]},
                        {"interval": [1, "day"]},
                    ]},
                    "name": "last_day_of_month",
                },
                {
                    "value": {"format_datetime": [
                        {"literal": "%Y%m%d"},
                        {"datetime": {"date_sub": [
                            {"date_trunc": [
                                {"date_add": ["full_date", {"interval": [1, "month"]}]},
                                "month",
                            ]},
                            {"interval": [1, "day"]},
                        ]}},
                    ]},
                    "name": "last_day_of_month_key",
                },
                {
                    "value": {"date_trunc": ["full_date", "month"]},
                    "name": "first_day_of_month",
                },
                {
                    "value": {"format_datetime": [
                        {"literal": "%Y%m%d"},
                        {"datetime": {"date_trunc": ["full_date", "month"]}},
                    ]},
                    "name": "first_day_of_month_key",
                },
            ],
            "from": [
                {
                    "value": {"unnest": {"generate_date_array": [
                        {"literal": "2000-01-01"},
                        {"date_add": [
                            {"last_day": ["current_date", "YEAR"]},
                            {"interval": [5, "year"]},
                        ]},
                        {"interval": [1, "day"]},
                    ]}},
                    "name": "full_date",
                },
                {
                    "left join": {"value": "financial_holiday", "name": "holiday"},
                    "on": {"eq": ["holiday.date", "full_date"]},
                },
            ],
        }
        self.assertEqual(result, expected)

    def test_issue_163_at_time_zone(self):
        result = parse(
            """
        SELECT
            REPLACE(CAST(EXTRACT(date from last_modified_date at time zone 'America/Sao_Paulo') AS STRING),'-','') as last_modified_date
        FROM
            territory2"""
        )
        expected = {
            "from": "territory2",
            "select": {
                "name": "last_modified_date",
                "value": {"replace": [
                    {"cast": [
                        {"extract": [
                            "date",
                            {"at_time_zone": [
                                "last_modified_date",
                                {"literal": "America/Sao_Paulo"},
                            ]},
                        ]},
                        {"string": {}},
                    ]},
                    {"literal": "-"},
                    {"literal": ""},
                ]},
            },
        }

        self.assertEqual(result, expected)
