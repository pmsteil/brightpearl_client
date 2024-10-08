#!/bin/bash

release=$1
commit_message=$2

#check that both args are passed
if [ -z "$release" ] || [ -z "$commit_message" ]; then
    echo "Usage: $0 <release> <commit_message>"
    exit 1
fi

echo "Tagging release $release with message: $commit_message"
read -p "Press Enter to continue..."

git add .
git commit -m "$commit_message"
git tag -a v$release -m "$commit_message"
git push origin v$release
git push
