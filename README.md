# autoloom
by vie mccoy, jessica taylor, and evan mcmullen for morpheus systems

autoloom is a program that allows you automatically navigate the latent space of base models.

instructions to use the lui (loom-terminal user interface):

make sure you have poetry installed and a .env file with your openai and hyperbolic api keys (in the autoloom directory)

```bash
git clone https://github.com/viemccoy/autoloom.git

cd autoloom

poetry install

poetry run lui
```

environment setup:

Create a `.env` file in ./autoloom with the following variables:

```env
HYPERBOLIC_API_KEY=your_hyperbolic_key_here
OPENAI_API_KEY=your_openai_key_here
```
