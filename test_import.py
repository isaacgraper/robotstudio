from robot_canvas.workspace.import_robot import import_robot_file
from pathlib import Path

doc = import_robot_file(Path("tests/golden/demo.robot"))
print("Name:", doc.name)
print("Tests:", len(doc.tests))
print("Keywords:", len(doc.keywords))
print("Libraries:", [l.name for l in doc.settings.libraries])
for test in doc.tests:
    print(f"  Test: {test.name}, steps: {len(test.steps)}")
    for step in test.steps:
        if step.type == "call":
            print(f"    call: {step.keyword.name}")
        elif step.type == "if":
            print(f"    if: {step.condition}")
        elif step.type == "for":
            print(f"    for: {step.variables} in {step.values}")
        elif step.type == "var":
            print(f"    var: {step.name} = {step.value}")
        else:
            print(f"    {step.type}")