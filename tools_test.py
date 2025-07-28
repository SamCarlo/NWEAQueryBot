import tools
import unittest
import config

def main():
    #####################
    ## TEST GET_SCHEMA ##
    #####################
    print()
    print("#" * 50)
    print("   TEST GET_SCHEMA   ".center(50, "#"))
    print("#" * 50)

    schema = tools.get_schema(db_path=config.anon_db_path)
    print(schema)

    #####################
    ## TEST SQL_QUERY  ##
    #####################
    print()
    print("#" * 50)
    print("   TEST SQL_QUERY   ".center(50, "#"))
    print("#" * 50)

    query = "SELECT * FROM results LIMIT 5;"
    sql_response = tools.sql_query(db_path=config.anon_db_path, query=query)
    print(sql_response)

    #########################
    ## TEST GET_TABLE_INFO ##
    #########################
    print()
    print("#" * 50)
    print("   TEST GET_TABLE_INFO   ".center(50, "#"))
    print("#" * 50)
    print()

    table_id = "results"
    table_info = tools.get_table_info(db_path=config.anon_db_path, table_id=table_id)
    print(table_info)

    ############################
    ## TEST TEMPLATE_RESPONSE ##
    ############################
    print()
    print("#" * 50)
    print("   TEST TEMPLATE_RESPONSE   ".center(50, "#"))
    print("#" * 50)
    print()
    output_text = "{s{9cac56fc06fe0ae372ea3e19644f0f540333b64de60fb16ed2ca1b794ae29b18}} is doing great."
    private_text = tools.template_response(output_text)
    print(private_text)
    print()
    print("#" * 50)
    print("   TESTING COMPLETE   ".center(50, "#"))
    print("#" * 50)
    print()

if __name__ == "__main__":
    main()