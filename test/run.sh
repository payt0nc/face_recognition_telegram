coverage run -m unittest discover -f -s "test/" -p "*.py" -v
coverage report -m --omit="*/test*"