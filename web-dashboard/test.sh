#!/bin/bash
echo "Starting Dashboard Tests..."

echo "Checking frontend build..."
cd /media/hzm/data_disk/EmbodiedAgentsSys/web-dashboard
pnpm build > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "✓ Frontend build OK"
else
  echo "✗ Frontend build FAIL"
  exit 1
fi

echo "Checking backend import..."
cd /media/hzm/data_disk/EmbodiedAgentsSys/examples
python3 -c "import agent_dashboard_backend; print('OK')" > /dev/null 2>&1
if [ $? -eq 0 ]; then
  echo "✓ Backend import OK"
else
  echo "✗ Backend import FAIL"
  exit 1
fi

echo "Done."
