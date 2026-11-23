from robot.api import get_model

source = """*** Settings ***
Library    Collections
Suite Setup    Log    start
Test Teardown    Log    end

*** Variables ***
${VAR}    value

*** Test Cases ***
Test
    [Documentation]    doc
    [Tags]    tag1    tag2
    [Setup]    Log    setup
    [Teardown]    Log    teardown
    [Timeout]    10s
    [Template]    Template
    Log    hello
    ${result} =    Get Length    abc

*** Keywords ***
My Keyword
    [Arguments]    ${arg1}    ${arg2}=default
    [Documentation]    keyword doc
    [Tags]    kwtag
    [Teardown]    Log    kw teardown
    Log    ${arg1}
    Log    ${arg2}
"""

m = get_model(source)
for sec in m.sections:
    print(f"\n=== Section: {type(sec).__name__} ===")
    print(f"  header: {sec.header.tokens[0].value if sec.header.tokens else 'none'}")
    if hasattr(sec, 'body'):
        for item in sec.body:
            print(f"  Item: {type(item).__name__}")
            if hasattr(item, 'name'):
                print(f"    name: {item.name}")
            if hasattr(item, 'header'):
                print(f"    header: {item.header}")
            if hasattr(item, 'body'):
                for stmt in item.body:
                    print(f"    stmt: {type(stmt).__name__} - tokens: {stmt.tokens}")
                    if hasattr(stmt, 'name'):
                        print(f"      name: {stmt.name}")
                    if hasattr(stmt, 'args'):
                        print(f"      args: {stmt.args}")
            if hasattr(item, 'tasks'):
                print(f"    tasks: {item.tasks}")