test_pysrc()
{
    path=$1
    name=${path##*/}
    echo "## $name"
    python $path
    echo ""
}

for file in `ls test/test_*.py`; do
    test_pysrc $file
done