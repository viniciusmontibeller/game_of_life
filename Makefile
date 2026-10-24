CC=gcc

CFLAGS = -O3 -Wall -Wextra
OMPFLAGS = -fopenmp

all: life life_parallel_simple life_parallel

life: life.c
	$(CC) $(CFLAGS) life.c -o life

life_parallel_simple: life_parallel_simple.c
	$(CC) $(CFLAGS) $(OMPFLAGS) life_parallel_simple.c -o life_parallel_simple

life_parallel: life_parallel.c
	$(CC) $(CFLAGS) $(OMPFLAGS) life_parallel.c -o life_parallel

clean:
	rm -f life life_parallel_simple life_parallel