all: rtl_fm

rtl_fm: rtl_fm.c convenience/convenience.c
	gcc -o rtl_fm rtl_fm.c convenience/convenience.c -lpthread -l rtlsdr -lm -lmysqlclient -lgps

clean:
	rm rtl_fm

