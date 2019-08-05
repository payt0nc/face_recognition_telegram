# Install dependencies
python3 -m pip install -r requirements.txt
python3 -m pip install -r dev-requirements.txt

# Setup pre-commit hook
root="$(pwd)"
rm -f $root/.git/hooks/*
cp $root/hooks/* $root/.git/hooks/
chmod +x $root/.git/hooks/pre-commit
