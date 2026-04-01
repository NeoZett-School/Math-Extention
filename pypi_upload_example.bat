@echo off
set version=%1
if "%version%"=="" (
    echo Usage: pypi_upload.bat [version]
    exit /b 1
)
echo Building distribution...
py -m build
echo Uploading to PyPI...
py -m twine upload dist/py_math_ext-%version%-py3-none-any.whl --verbose -u __token__ -p <insert token here>
echo Done.
exit /b 0