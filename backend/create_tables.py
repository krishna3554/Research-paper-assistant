from db import Base, engine
from models import DocumentChunk, Paper

def main():
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully")

if __name__ == "__main__":
    main()