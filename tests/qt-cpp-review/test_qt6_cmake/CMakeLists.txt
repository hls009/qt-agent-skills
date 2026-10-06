# Negative fixture for qt_review_lint.py QT6-14..QT6-17.
# This file is INTENTIONALLY wrong for a Qt 5 project: each line below must
# produce one finding. It is never configured or built by the test suite.

find_package(Qt6 6.8 REQUIRED COMPONENTS Widgets Quick)          # QT6-15
qt_standard_project_setup(REQUIRES 6.8)                          # QT6-14
qt_add_executable(myapp main.cpp)                                # QT6-14
qt_add_qml_module(myapp URI MyApp QML_FILES Main.qml)            # QT6-14 + QT6-16
target_link_libraries(myapp PRIVATE Qt6::Widgets Qt5::Quick)     # QT6-15 + QT6-17
qt_add_translations(myapp TS_FILES app_de.ts)                    # QT6-14

set(QML_DIR_FILES qml/qmldir)                                       # QT6-16
