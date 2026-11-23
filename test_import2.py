from robot_canvas.workspace.import_robot import import_robot_file
from robot_canvas.generator.writer import write_document
from pathlib import Path

# Test with a more complex suite
complex_robot = """*** Settings ***
Library    Collections
Suite Setup    Log    Suite Start
Test Teardown    Log    Test End
Force Tags    smoke
Default Tags    default

*** Variables ***
${GLOBAL_VAR}    global_value
@{LIST_VAR}    item1    item2

*** Test Cases ***
Simple Test
    [Documentation]    A simple test
    [Tags]    tag1    tag2
    [Setup]    Log    Test Setup
    [Teardown]    Log    Test Teardown
    [Timeout]    10s
    Log    Hello
    ${result} =    Get Length    abc
    Should Be Equal    ${result}    3

For Loop Test
    [Documentation]    Test FOR loop
    FOR    ${item}    IN    @{LIST_VAR}
        Log    ${item}
    END
    FOR    ${i}    IN RANGE    10
        Log    ${i}
    END

While Loop Test
    [Documentation]    Test WHILE loop
    ${x} =    Set Variable    0
    WHILE    ${x} < 5
        Log    ${x}
        ${x} =    Evaluate    ${x} + 1
    END

If Else Test
    [Documentation]    Test IF/ELSE
    ${value} =    Set Variable    42
    IF    ${value} > 10
        Log    Large
    ELSE IF    ${value} == 10
        Log    Ten
    ELSE
        Log    Small
    END

Try Except Test
    [Documentation]    Test TRY/EXCEPT
    TRY
        Fail    This fails
    EXCEPT
        Log    Caught error
    ELSE
        Log    No error
    FINALLY
        Log    Finally done
    END

Var Return Break Continue Test
    [Documentation]    Test VAR, RETURN, BREAK, CONTINUE
    VAR    ${my_var}    value    scope=TEST
    RETURN    ${my_var}
    FOR    ${i}    IN RANGE    10
        BREAK
        CONTINUE
    END

*** Keywords ***
User Keyword
    [Arguments]    ${arg1}    ${arg2}=default
    [Documentation]    A user keyword
    [Tags]    kwtag
    [Teardown]    Log    Keyword teardown
    Log    ${arg1}
    Log    ${arg2}
    RETURN    ${arg1}
"""

# Write to a temp file
import tempfile
with tempfile.NamedTemporaryFile(mode='w', suffix='.robot', delete=False, encoding='utf-8') as f:
    f.write(complex_robot)
    temp_path = f.name

try:
    doc = import_robot_file(Path(temp_path))
    print("Name:", doc.name)
    print("Tests:", len(doc.tests))
    print("Keywords:", len(doc.keywords))
    print("Libraries:", [l.name for l in doc.settings.libraries])
    print("Variables:", [(v.name, v.value) for v in doc.settings.variables])
    print("Force Tags:", doc.settings.force_tags)
    print("Default Tags:", doc.settings.default_tags)
    print()

    for test in doc.tests:
        print(f"Test: {test.name}")
        print(f"  Doc: {test.documentation}")
        print(f"  Tags: {test.tags}")
        print(f"  Setup: {test.setup.keyword.name if test.setup else None}")
        print(f"  Teardown: {test.setup.keyword.name if test.teardown else None}")
        print(f"  Timeout: {test.timeout}")
        print(f"  Steps: {len(test.steps)}")
        for step in test.steps:
            if step.type == "call":
                print(f"    call: {step.keyword.name} args={[(a.name, a.value) for a in step.args]} assign={step.assign}")
            elif step.type == "if":
                print(f"    if: {step.condition}")
                print(f"      then: {len(step.steps)} steps")
                print(f"      elseif: {len(step.branches)} branches")
                print(f"      else: {len(step.else_steps)} steps")
            elif step.type == "for":
                print(f"    for: {step.variables} in {step.values} flavor={step.flavor}")
                print(f"      steps: {len(step.steps)}")
            elif step.type == "while":
                print(f"    while: {step.condition} limit={step.limit} until={step.until}")
                print(f"      steps: {len(step.steps)}")
            elif step.type == "try":
                print(f"    try: {len(step.steps)} steps, {len(step.excepts)} excepts, else={len(step.else_steps)}, finally={len(step.finally_steps)}")
            elif step.type == "var":
                print(f"    var: {step.name} = {step.value} scope={step.scope}")
            elif step.type == "return":
                print(f"    return: {step.values}")
            elif step.type == "break":
                print(f"    break")
            elif step.type == "continue":
                print(f"    continue")
            elif step.type == "comment":
                print(f"    comment: {step.text}")
            elif step.type == "raw":
                print(f"    raw: {step.lines}")
        print()

    for kw in doc.keywords:
        print(f"Keyword: {kw.name}")
        print(f"  Args: {kw.arguments}")
        print(f"  Doc: {kw.documentation}")
        print(f"  Tags: {kw.tags}")
        print(f"  Steps: {len(kw.steps)}")
        for step in kw.steps:
            if step.type == "call":
                print(f"    call: {step.keyword.name} args={[(a.name, a.value) for a in step.args]}")
            elif step.type == "return":
                print(f"    return: {step.values}")
        print()

    # Test round-trip: generate .robot from imported model
    generated = write_document(doc)
    print("Generated .robot:")
    print(generated[:2000])
    print("... (truncated)")

finally:
    import os
    os.unlink(temp_path)