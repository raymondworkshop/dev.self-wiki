
#### self-wiki  

##### the architecture
* Push intelligence up into skills, and push execution down into deterministic tooling. keep the harness thin.  
    - Fast skills sit on top
        + markdown procedures that **encode judgement, process, and domain knowledge** 
    - thin cli harness sits in the middle.
        + JSON in, text out. Read-only by default.
    - deterministic is where trust lives. 
        + Same input, same output. Every time. SQL queris. Compiled code. ARITHMETIC.



* a skill file tell the model how
    - works like a method call 

* the harness is the program that runs the LLM  
    - runs the model in a loop,
    reads and writes your files, manages context, and enforces safety.

* Resolvers tell it what to load and when  
    - The description is the resolver.
    Every skill has a description field, and the model matches user intent to skill descriptions automatically.

* latent space vs deterministic space  
    - latent spcae is where intelligence lives
    - deterministic is where trust lives  

* Diarization is the step that makes AI useful for real knowledge work

#### references
* [Thin Harness, Fat Skills](https://x.com/garrytan/status/2042925773300908103)