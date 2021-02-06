CREATE TABLE car (
    car_id INTEGER,
    make VARCHAR(64) NOT NULL,
    model VARCHAR(256) NOT NULL,
    year DECIMAL(4, 0) NOT NULL,
    PRIMARY KEY(car_id)
);

CREATE TABLE part (
    part_id INTEGER,
    name VARCHAR(256) NOT NULL,
    description VARCHAR(1024),
    manufacturers_partnum VARCHAR(256),
    price DECIMAL(10, 2),
    PRIMARY KEY(part_id)
);

CREATE TABLE car_part (
    car_id INTEGER,
    part_id INTEGER,
    FOREIGN KEY(car_id) REFERENCES car(car_id),
    FOREIGN KEY(part_id) REFERENCES part(part_id),
    PRIMARY KEY(car_id, part_id)
);

INSERT INTO car VALUES (0, 'HONDA', 'CIVIC', 2005);
INSERT INTO car VALUES (1, 'TOYOTA', 'COROLLA', 2010);
INSERT INTO car VALUES (2, 'FORD', 'F-150', 2009);
INSERT INTO part
VALUES (0, 'Brake Pads', 'Duralast ceramic brake pads', 'MKD621', 19.99);
INSERT INTO part
VALUES (1, 'Alternator', 'Duralast gold new alternator', 'DLG12308', 175.99);
INSERT INTO part
VALUES (2, 'Radiator Cap', 'Duralast Radiator Cap', '7036', 10.99);
INSERT INTO part
VALUES (3, 'Alternator', 'Duralast gold new alternator', 'DLG5540-17-2',
    256.99);
INSERT INTO part
VALUES (4, 'Rear Leaf Spring', '1500lbs capacity', '43-1781', 129.99);

INSERT INTO car_part VALUES (0, 0);
INSERT INTO car_part VALUES (0, 1);
INSERT INTO car_part VALUES (0, 2);
INSERT INTO car_part VALUES (1, 2);
INSERT INTO car_part VALUES (1, 3);
INSERT INTO car_part VALUES (2, 2);
INSERT INTO car_part VALUES (2, 4);