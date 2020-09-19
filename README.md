# hurricane-deploy
The deployment respoitory for a hurricane forecasting system based on machine
learning and deep learning methods

# Quickstart

## Import most recent Atlantic tropic storms

From this NHC resource described here, , we can import the most recent tropical
storms using the following code.

```python
import update.py
results = update.nhc()
```